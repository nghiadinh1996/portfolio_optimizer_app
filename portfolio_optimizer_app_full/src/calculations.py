from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

ReturnMethod = Literal["manual_expected", "historical"]


@dataclass(frozen=True)
class RiskReturnModel:
    """Risk-return inputs used by the optimizer."""

    monthly_returns: pd.DataFrame
    demeaned_returns: pd.DataFrame
    covariance_monthly: pd.DataFrame
    correlation: pd.DataFrame
    expected_annual_returns: pd.Series
    expected_monthly_returns: pd.Series
    historical_annual_returns: pd.Series
    historical_annual_volatility: pd.Series
    return_method: str


def calculate_monthly_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Calculate periodic returns from price/index levels.

    The first price row is dropped because it has no previous period.
    """
    if "Date" not in prices.columns:
        raise ValueError("prices must contain a Date column")

    assets = [c for c in prices.columns if c != "Date"]
    returns = prices[assets].pct_change().iloc[1:].copy()
    returns.insert(0, "Date", prices["Date"].iloc[1:].values)
    return returns.reset_index(drop=True)


def calculate_demeaned_returns(monthly_returns: pd.DataFrame) -> pd.DataFrame:
    """Calculate demeaned returns: asset return minus its own average return."""
    assets = [c for c in monthly_returns.columns if c != "Date"]
    demeaned = monthly_returns[assets] - monthly_returns[assets].mean(axis=0)
    demeaned.insert(0, "Date", monthly_returns["Date"].values)
    return demeaned.reset_index(drop=True)


def calculate_covariance_matrix(monthly_returns: pd.DataFrame, ddof: int = 0) -> pd.DataFrame:
    """Calculate the monthly covariance matrix.

    ddof=0 matches the population covariance logic used in the Excel workbook.
    """
    assets = [c for c in monthly_returns.columns if c != "Date"]
    return monthly_returns[assets].cov(ddof=ddof)


def calculate_correlation_matrix(monthly_returns: pd.DataFrame) -> pd.DataFrame:
    assets = [c for c in monthly_returns.columns if c != "Date"]
    return monthly_returns[assets].corr()


def annual_to_monthly_return(annual_returns: pd.Series | float) -> pd.Series | float:
    return (1 + annual_returns) ** (1 / 12) - 1


def monthly_to_annual_return(monthly_returns: pd.Series | float) -> pd.Series | float:
    return (1 + monthly_returns) ** 12 - 1


def annualize_volatility(monthly_volatility: pd.Series | float) -> pd.Series | float:
    return monthly_volatility * np.sqrt(12)


def historical_annual_returns(monthly_returns: pd.DataFrame) -> pd.Series:
    assets = [c for c in monthly_returns.columns if c != "Date"]
    avg_monthly = monthly_returns[assets].mean(axis=0)
    result = monthly_to_annual_return(avg_monthly)
    result.name = "Historical Annual Return"
    return result


def historical_annual_volatility(monthly_returns: pd.DataFrame, ddof: int = 0) -> pd.Series:
    assets = [c for c in monthly_returns.columns if c != "Date"]
    monthly_vol = monthly_returns[assets].std(axis=0, ddof=ddof)
    result = annualize_volatility(monthly_vol)
    result.name = "Historical Annual Volatility"
    return result


def build_risk_return_model(
    prices: pd.DataFrame,
    manual_expected_annual_returns: pd.Series,
    return_method: ReturnMethod = "manual_expected",
    covariance_ddof: int = 0,
) -> RiskReturnModel:
    """Build all core calculations needed for optimization."""
    monthly_returns = calculate_monthly_returns(prices)
    demeaned_returns = calculate_demeaned_returns(monthly_returns)
    cov_monthly = calculate_covariance_matrix(monthly_returns, ddof=covariance_ddof)
    corr = calculate_correlation_matrix(monthly_returns)
    hist_annual = historical_annual_returns(monthly_returns)
    hist_vol = historical_annual_volatility(monthly_returns, ddof=covariance_ddof)

    if return_method == "manual_expected":
        expected_annual = manual_expected_annual_returns.copy()
    elif return_method == "historical":
        expected_annual = hist_annual.copy()
        expected_annual.name = "Expected Annual Return"
    else:
        raise ValueError("return_method must be 'manual_expected' or 'historical'")

    expected_monthly = annual_to_monthly_return(expected_annual)
    expected_monthly.name = "Expected Monthly Return"

    return RiskReturnModel(
        monthly_returns=monthly_returns,
        demeaned_returns=demeaned_returns,
        covariance_monthly=cov_monthly,
        correlation=corr,
        expected_annual_returns=expected_annual,
        expected_monthly_returns=expected_monthly,
        historical_annual_returns=hist_annual,
        historical_annual_volatility=hist_vol,
        return_method=return_method,
    )


def portfolio_annual_return(weights: np.ndarray, expected_annual_returns: pd.Series) -> float:
    weights = np.asarray(weights, dtype=float)
    return float(weights @ expected_annual_returns.values)


def portfolio_annual_volatility(weights: np.ndarray, covariance_monthly: pd.DataFrame) -> float:
    weights = np.asarray(weights, dtype=float)
    monthly_var = float(weights.T @ covariance_monthly.values @ weights)
    monthly_vol = np.sqrt(max(monthly_var, 0.0))
    return float(monthly_vol * np.sqrt(12))


def portfolio_sharpe_ratio(
    weights: np.ndarray,
    expected_annual_returns: pd.Series,
    covariance_monthly: pd.DataFrame,
    risk_free_rate: float,
) -> float:
    vol = portfolio_annual_volatility(weights, covariance_monthly)
    if vol == 0:
        return np.nan
    ret = portfolio_annual_return(weights, expected_annual_returns)
    return float((ret - risk_free_rate) / vol)


def portfolio_metrics(
    weights: pd.Series,
    expected_annual_returns: pd.Series,
    covariance_monthly: pd.DataFrame,
    risk_free_rate: float,
) -> dict[str, float]:
    """Return annual return, annual volatility, and standard Sharpe ratio."""
    aligned_weights = weights.reindex(expected_annual_returns.index).fillna(0.0)
    w = aligned_weights.values.astype(float)
    ann_return = portfolio_annual_return(w, expected_annual_returns)
    ann_vol = portfolio_annual_volatility(w, covariance_monthly.loc[expected_annual_returns.index, expected_annual_returns.index])
    sharpe = np.nan if ann_vol == 0 else (ann_return - risk_free_rate) / ann_vol
    return {
        "Annual Return": float(ann_return),
        "Annual Volatility": float(ann_vol),
        "Sharpe Ratio": float(sharpe),
    }


def equal_weight_series(assets: list[str]) -> pd.Series:
    if not assets:
        raise ValueError("assets cannot be empty")
    return pd.Series(1 / len(assets), index=assets, name="Equal Weight")


def build_asset_summary(asset_info: pd.DataFrame, model: RiskReturnModel) -> pd.DataFrame:
    summary = asset_info.copy()
    summary = summary.merge(
        model.expected_annual_returns.rename("Expected Annual Return"),
        left_on="Asset",
        right_index=True,
        how="left",
    )
    summary = summary.merge(
        model.historical_annual_returns.rename("Historical Annual Return"),
        left_on="Asset",
        right_index=True,
        how="left",
    )
    summary = summary.merge(
        model.historical_annual_volatility.rename("Historical Annual Volatility"),
        left_on="Asset",
        right_index=True,
        how="left",
    )
    return summary
