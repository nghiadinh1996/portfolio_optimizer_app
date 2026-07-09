from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ConstraintConfig:
    """Optional portfolio constraints selected by the user.

    All percentages are expressed as decimals. Example: 60% = 0.60.
    A None value means the constraint is inactive.
    """

    no_short: bool = True
    individual_min: float | None = None
    individual_max: float | None = None
    equity_min: float | None = None
    equity_max: float | None = None
    fixed_income_min: float | None = None
    fixed_income_max: float | None = None
    cash_min: float | None = None
    cash_max: float | None = None
    developed_min: float | None = None
    developed_max: float | None = None
    emerging_min: float | None = None
    emerging_max: float | None = None
    foreign_equity_max_pct_of_equity: float | None = None


def _mask(asset_info: pd.DataFrame, assets: list[str], column: str, value: str) -> np.ndarray:
    lookup = asset_info.set_index("Asset").loc[assets]
    return lookup[column].astype(str).str.lower().eq(value.lower()).to_numpy(dtype=float)


def _combined_mask(
    asset_info: pd.DataFrame,
    assets: list[str],
    conditions: list[tuple[str, str]],
) -> np.ndarray:
    lookup = asset_info.set_index("Asset").loc[assets]
    bool_mask = np.ones(len(assets), dtype=bool)
    for column, value in conditions:
        bool_mask &= lookup[column].astype(str).str.lower().eq(value.lower()).to_numpy()
    return bool_mask.astype(float)


def group_weight(weights: np.ndarray, mask: np.ndarray) -> float:
    return float(np.asarray(weights, dtype=float) @ mask)


def build_bounds(n_assets: int, config: ConstraintConfig) -> list[tuple[float | None, float | None]]:
    lower = 0.0 if config.no_short else None
    upper = 1.0

    if config.individual_min is not None:
        lower = max(lower or 0.0, config.individual_min) if config.no_short else config.individual_min
    if config.individual_max is not None:
        upper = min(upper, config.individual_max)

    if lower is not None and upper is not None and lower > upper:
        raise ValueError("Individual minimum weight cannot be greater than individual maximum weight.")
    if lower is not None and lower * n_assets > 1 + 1e-10:
        raise ValueError("Individual minimum weight is too high to create a fully invested portfolio.")
    if upper is not None and upper * n_assets < 1 - 1e-10:
        raise ValueError("Individual maximum weight is too low to create a fully invested portfolio.")

    return [(lower, upper) for _ in range(n_assets)]


def _add_group_min_max(
    constraints: list[dict],
    mask: np.ndarray,
    min_value: float | None,
    max_value: float | None,
    label: str,
) -> None:
    if min_value is not None:
        constraints.append({
            "type": "ineq",
            "fun": lambda w, m=mask, v=min_value: group_weight(w, m) - v,
            "label": f"{label} minimum",
        })
    if max_value is not None:
        constraints.append({
            "type": "ineq",
            "fun": lambda w, m=mask, v=max_value: v - group_weight(w, m),
            "label": f"{label} maximum",
        })


def build_scipy_constraints(
    assets: list[str],
    asset_info: pd.DataFrame,
    config: ConstraintConfig,
    extra_constraints: list[dict] | None = None,
) -> list[dict]:
    """Build scipy SLSQP constraints.

    SLSQP inequality constraints are written as function(weights) >= 0.
    """
    constraints: list[dict] = [
        {"type": "eq", "fun": lambda w: np.sum(w) - 1.0, "label": "fully invested"}
    ]

    equity_mask = _mask(asset_info, assets, "Asset Class", "Equity")
    fixed_income_mask = _mask(asset_info, assets, "Asset Class", "Fixed Income")
    cash_mask = _mask(asset_info, assets, "Asset Class", "Cash")
    developed_mask = _mask(asset_info, assets, "Subgroup", "Developed")
    emerging_mask = _mask(asset_info, assets, "Subgroup", "Emerging")
    foreign_equity_mask = _combined_mask(
        asset_info,
        assets,
        [("Asset Class", "Equity"), ("Region", "Foreign")],
    )

    _add_group_min_max(constraints, equity_mask, config.equity_min, config.equity_max, "Equity")
    _add_group_min_max(
        constraints,
        fixed_income_mask,
        config.fixed_income_min,
        config.fixed_income_max,
        "Fixed income",
    )
    _add_group_min_max(constraints, cash_mask, config.cash_min, config.cash_max, "Cash")
    _add_group_min_max(constraints, developed_mask, config.developed_min, config.developed_max, "Developed")
    _add_group_min_max(constraints, emerging_mask, config.emerging_min, config.emerging_max, "Emerging")

    if config.foreign_equity_max_pct_of_equity is not None:
        pct = config.foreign_equity_max_pct_of_equity
        constraints.append({
            "type": "ineq",
            "fun": lambda w, fe=foreign_equity_mask, eq=equity_mask, p=pct: p * group_weight(w, eq) - group_weight(w, fe),
            "label": "Foreign equity as percent of equity maximum",
        })

    if extra_constraints:
        constraints.extend(extra_constraints)

    # scipy.optimize.minimize only expects type and fun, so remove internal labels.
    return [{"type": c["type"], "fun": c["fun"]} for c in constraints]


def summarize_group_weights(
    weights: pd.Series,
    asset_info: pd.DataFrame,
) -> dict[str, float]:
    """Calculate important group weights for reporting."""
    assets = list(weights.index)
    w = weights.to_numpy(dtype=float)
    equity_mask = _mask(asset_info, assets, "Asset Class", "Equity")
    fixed_income_mask = _mask(asset_info, assets, "Asset Class", "Fixed Income")
    cash_mask = _mask(asset_info, assets, "Asset Class", "Cash")
    developed_mask = _mask(asset_info, assets, "Subgroup", "Developed")
    emerging_mask = _mask(asset_info, assets, "Subgroup", "Emerging")
    foreign_equity_mask = _combined_mask(asset_info, assets, [("Asset Class", "Equity"), ("Region", "Foreign")])

    equity = group_weight(w, equity_mask)
    foreign_equity = group_weight(w, foreign_equity_mask)
    return {
        "Equity": equity,
        "Fixed Income": group_weight(w, fixed_income_mask),
        "Cash": group_weight(w, cash_mask),
        "Developed": group_weight(w, developed_mask),
        "Emerging": group_weight(w, emerging_mask),
        "Foreign Equity": foreign_equity,
        "Foreign Equity / Equity": np.nan if equity == 0 else foreign_equity / equity,
    }
