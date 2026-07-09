from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from src.calculations import RiskReturnModel
from src.constraints import ConstraintConfig


@dataclass(frozen=True)
class ValidationReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.errors


def _pct(value: float | None) -> str:
    if value is None:
        return "inactive"
    return f"{value:.2%}"


def _check_range(label: str, min_value: float | None, max_value: float | None, errors: list[str]) -> None:
    for kind, value in [("minimum", min_value), ("maximum", max_value)]:
        if value is not None and not 0 <= value <= 1:
            errors.append(f"{label} {kind} must be between 0% and 100%. Current value: {value:.2%}.")
    if min_value is not None and max_value is not None and min_value > max_value:
        errors.append(f"{label} minimum cannot be greater than {label} maximum.")


def _group_exists(asset_info: pd.DataFrame, column: str, value: str) -> bool:
    return asset_info[column].astype(str).str.lower().eq(value.lower()).any()


def _subgroup_exists(asset_info: pd.DataFrame, value: str) -> bool:
    return _group_exists(asset_info, "Subgroup", value)


def validate_constraint_config(asset_info: pd.DataFrame, config: ConstraintConfig) -> ValidationReport:
    """Validate active constraint settings before calling scipy."""
    errors: list[str] = []
    warnings: list[str] = []
    n_assets = len(asset_info)

    _check_range("Individual asset", config.individual_min, config.individual_max, errors)
    _check_range("Equity", config.equity_min, config.equity_max, errors)
    _check_range("Fixed income", config.fixed_income_min, config.fixed_income_max, errors)
    _check_range("Cash", config.cash_min, config.cash_max, errors)
    _check_range("Developed", config.developed_min, config.developed_max, errors)
    _check_range("Emerging", config.emerging_min, config.emerging_max, errors)

    if config.individual_min is not None and config.individual_min * n_assets > 1 + 1e-10:
        errors.append(
            "Individual asset minimum is too high. "
            f"With {n_assets} assets, {config.individual_min:.2%} minimum requires more than 100% total weight."
        )
    if config.individual_max is not None and config.individual_max * n_assets < 1 - 1e-10:
        errors.append(
            "Individual asset maximum is too low. "
            f"With {n_assets} assets, {config.individual_max:.2%} maximum cannot reach 100% total weight."
        )

    if config.equity_min and not _group_exists(asset_info, "Asset Class", "Equity"):
        errors.append("Equity minimum is active, but no asset is classified as Equity.")
    if config.fixed_income_min and not _group_exists(asset_info, "Asset Class", "Fixed Income"):
        errors.append("Fixed income minimum is active, but no asset is classified as Fixed Income.")
    if config.cash_min and not _group_exists(asset_info, "Asset Class", "Cash"):
        errors.append("Cash minimum is active, but no asset is classified as Cash.")
    if config.developed_min and not _subgroup_exists(asset_info, "Developed"):
        errors.append("Developed minimum is active, but no asset has Subgroup = Developed.")
    if config.emerging_min and not _subgroup_exists(asset_info, "Emerging"):
        errors.append("Emerging minimum is active, but no asset has Subgroup = Emerging.")

    # Equity, fixed income, and cash should be mutually exclusive asset classes in this template.
    major_min_sum = sum(v or 0 for v in [config.equity_min, config.fixed_income_min, config.cash_min])
    if major_min_sum > 1 + 1e-10:
        errors.append(
            "The sum of active Equity, Fixed Income, and Cash minimums exceeds 100%. "
            f"Current sum: {major_min_sum:.2%}."
        )

    # Developed and emerging are subgroups and may be a subset of equity in the standard template.
    sub_min_sum = sum(v or 0 for v in [config.developed_min, config.emerging_min])
    if config.equity_max is not None and sub_min_sum > config.equity_max + 1e-10:
        errors.append(
            "Developed + Emerging minimums exceed the Equity maximum. "
            f"Developed + Emerging min: {sub_min_sum:.2%}; Equity max: {config.equity_max:.2%}."
        )

    if config.foreign_equity_max_pct_of_equity is not None:
        pct = config.foreign_equity_max_pct_of_equity
        if not 0 <= pct <= 1:
            errors.append("Foreign equity maximum as % of equity must be between 0% and 100%.")
        if not _group_exists(asset_info, "Asset Class", "Equity"):
            warnings.append("Foreign equity constraint is active, but no Equity asset exists.")
        if not _group_exists(asset_info, "Region", "Foreign"):
            warnings.append("Foreign equity constraint is active, but no Foreign asset exists. The constraint will not bind.")

    if not config.no_short:
        warnings.append("Short selling is allowed. Some optimized portfolios may contain negative weights.")

    return ValidationReport(errors=errors, warnings=warnings)


def validate_risk_return_model(model: RiskReturnModel) -> ValidationReport:
    """Validate model outputs before optimization."""
    errors: list[str] = []
    warnings: list[str] = []

    if model.monthly_returns.empty:
        errors.append("No monthly returns were calculated. Check the prices sheet.")

    assets = [c for c in model.monthly_returns.columns if c != "Date"]
    if len(model.monthly_returns) < 12:
        warnings.append(
            "Fewer than 12 return observations were found. Annualized return and volatility may be unreliable."
        )

    if model.monthly_returns[assets].isna().any().any():
        errors.append("Calculated monthly returns contain missing values.")

    if not np.isfinite(model.covariance_monthly.to_numpy(dtype=float)).all():
        errors.append("The covariance matrix contains non-finite values.")

    vol = model.historical_annual_volatility
    zero_vol_assets = vol[vol <= 1e-12].index.tolist()
    if zero_vol_assets:
        warnings.append(
            "The following asset(s) have near-zero historical volatility, which can make Sharpe optimization unstable: "
            + ", ".join(zero_vol_assets)
        )

    suspicious_return_assets = model.expected_annual_returns[model.expected_annual_returns.abs() > 1.0].index.tolist()
    if suspicious_return_assets:
        errors.append(
            "Expected annual returns appear to be entered as whole percentages instead of decimals for: "
            + ", ".join(suspicious_return_assets)
        )

    return ValidationReport(errors=errors, warnings=warnings)


def build_constraint_settings_table(config: ConstraintConfig) -> pd.DataFrame:
    rows = [
        {"Setting": "No short selling", "Value": "Yes" if config.no_short else "No"},
        {"Setting": "Individual asset min", "Value": _pct(config.individual_min)},
        {"Setting": "Individual asset max", "Value": _pct(config.individual_max)},
        {"Setting": "Equity min", "Value": _pct(config.equity_min)},
        {"Setting": "Equity max", "Value": _pct(config.equity_max)},
        {"Setting": "Fixed income min", "Value": _pct(config.fixed_income_min)},
        {"Setting": "Fixed income max", "Value": _pct(config.fixed_income_max)},
        {"Setting": "Cash min", "Value": _pct(config.cash_min)},
        {"Setting": "Cash max", "Value": _pct(config.cash_max)},
        {"Setting": "Developed min", "Value": _pct(config.developed_min)},
        {"Setting": "Developed max", "Value": _pct(config.developed_max)},
        {"Setting": "Emerging min", "Value": _pct(config.emerging_min)},
        {"Setting": "Emerging max", "Value": _pct(config.emerging_max)},
        {"Setting": "Foreign equity max / equity", "Value": _pct(config.foreign_equity_max_pct_of_equity)},
    ]
    return pd.DataFrame(rows)
