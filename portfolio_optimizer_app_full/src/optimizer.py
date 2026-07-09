from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from src.calculations import (
    RiskReturnModel,
    portfolio_annual_return,
    portfolio_annual_volatility,
    portfolio_metrics,
    portfolio_sharpe_ratio,
)
from src.constraints import ConstraintConfig, build_bounds, build_scipy_constraints

ObjectiveName = Literal[
    "max_return",
    "min_volatility",
    "max_sharpe",
    "target_return",
    "target_risk",
]


@dataclass(frozen=True)
class OptimizationResult:
    name: str
    success: bool
    message: str
    weights: pd.Series | None
    metrics: dict[str, float] | None
    raw_objective_value: float | None = None


def _initial_weights(n_assets: int, bounds: list[tuple[float | None, float | None]]) -> np.ndarray:
    """Create a reasonable starting point for SLSQP.

    This starts from equal weight and clips to active bounds, then normalizes.
    """
    x0 = np.repeat(1.0 / n_assets, n_assets)
    lower = np.array([0.0 if lo is None else lo for lo, _ in bounds], dtype=float)
    upper = np.array([1.0 if hi is None else hi for _, hi in bounds], dtype=float)
    x0 = np.clip(x0, lower, upper)

    remaining = 1.0 - lower.sum()
    capacity = upper - lower
    if remaining < -1e-10 or capacity.sum() < remaining - 1e-10:
        return np.repeat(1.0 / n_assets, n_assets)

    if abs(x0.sum() - 1.0) > 1e-10:
        if capacity.sum() > 0:
            x0 = lower + capacity / capacity.sum() * remaining
        else:
            x0 = np.repeat(1.0 / n_assets, n_assets)
    return x0


def _objective_function(
    objective: ObjectiveName,
    model: RiskReturnModel,
    risk_free_rate: float,
):
    expected = model.expected_annual_returns
    cov = model.covariance_monthly

    if objective in {"max_return", "target_risk"}:
        return lambda w: -portfolio_annual_return(w, expected)
    if objective in {"min_volatility", "target_return"}:
        return lambda w: portfolio_annual_volatility(w, cov)
    if objective == "max_sharpe":
        return lambda w: -portfolio_sharpe_ratio(w, expected, cov, risk_free_rate)
    raise ValueError(f"Unsupported objective: {objective}")


def optimize_portfolio(
    name: str,
    objective: ObjectiveName,
    model: RiskReturnModel,
    asset_info: pd.DataFrame,
    config: ConstraintConfig,
    risk_free_rate: float = 0.0,
    target_return: float | None = None,
    target_risk: float | None = None,
    max_iter: int = 1000,
) -> OptimizationResult:
    """Run one constrained portfolio optimization."""
    assets = list(model.expected_annual_returns.index)
    n_assets = len(assets)
    bounds = build_bounds(n_assets, config)

    extra_constraints: list[dict] = []
    if objective == "target_return":
        if target_return is None:
            raise ValueError("target_return is required for target_return optimization")
        extra_constraints.append({
            "type": "ineq",
            "fun": lambda w, tr=target_return: portfolio_annual_return(w, model.expected_annual_returns) - tr,
        })
    if objective == "target_risk":
        if target_risk is None:
            raise ValueError("target_risk is required for target_risk optimization")
        extra_constraints.append({
            "type": "ineq",
            "fun": lambda w, tv=target_risk: tv - portfolio_annual_volatility(w, model.covariance_monthly),
        })

    constraints = build_scipy_constraints(assets, asset_info, config, extra_constraints=extra_constraints)
    x0 = _initial_weights(n_assets, bounds)
    objective_function = _objective_function(objective, model, risk_free_rate)

    result = minimize(
        objective_function,
        x0=x0,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
        options={"maxiter": max_iter, "ftol": 1e-12, "disp": False},
    )

    if not result.success:
        return OptimizationResult(
            name=name,
            success=False,
            message=str(result.message),
            weights=None,
            metrics=None,
            raw_objective_value=None,
        )

    weights = pd.Series(result.x, index=assets, name=name)
    weights = weights.where(weights.abs() > 1e-8, 0.0)
    # Clean tiny numerical drift while preserving sum close to 1.
    if abs(weights.sum() - 1.0) > 1e-8 and weights.sum() != 0:
        weights = weights / weights.sum()

    metrics = portfolio_metrics(weights, model.expected_annual_returns, model.covariance_monthly, risk_free_rate)
    return OptimizationResult(
        name=name,
        success=True,
        message="Optimization successful",
        weights=weights,
        metrics=metrics,
        raw_objective_value=float(result.fun),
    )


def run_standard_optimizations(
    model: RiskReturnModel,
    asset_info: pd.DataFrame,
    config: ConstraintConfig,
    risk_free_rate: float,
) -> dict[str, OptimizationResult]:
    """Run the three standard optimized portfolios."""
    return {
        "Max Return": optimize_portfolio(
            "Max Return", "max_return", model, asset_info, config, risk_free_rate
        ),
        "Min Volatility": optimize_portfolio(
            "Min Volatility", "min_volatility", model, asset_info, config, risk_free_rate
        ),
        "Max Sharpe": optimize_portfolio(
            "Max Sharpe", "max_sharpe", model, asset_info, config, risk_free_rate
        ),
    }


def successful_results(results: dict[str, OptimizationResult]) -> dict[str, OptimizationResult]:
    return {name: result for name, result in results.items() if result.success}
