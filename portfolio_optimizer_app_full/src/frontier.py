from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.constraints import ConstraintConfig
from src.optimizer import OptimizationResult, optimize_portfolio
from src.calculations import RiskReturnModel


@dataclass(frozen=True)
class FeasibleRange:
    min_volatility_result: OptimizationResult
    max_return_result: OptimizationResult

    @property
    def min_volatility(self) -> float | None:
        if not self.min_volatility_result.metrics:
            return None
        return self.min_volatility_result.metrics["Annual Volatility"]

    @property
    def return_at_min_volatility(self) -> float | None:
        if not self.min_volatility_result.metrics:
            return None
        return self.min_volatility_result.metrics["Annual Return"]

    @property
    def max_return(self) -> float | None:
        if not self.max_return_result.metrics:
            return None
        return self.max_return_result.metrics["Annual Return"]


def estimate_feasible_range(
    model: RiskReturnModel,
    asset_info: pd.DataFrame,
    config: ConstraintConfig,
    risk_free_rate: float,
) -> FeasibleRange:
    min_vol = optimize_portfolio(
        "Min Volatility", "min_volatility", model, asset_info, config, risk_free_rate
    )
    max_ret = optimize_portfolio(
        "Max Return", "max_return", model, asset_info, config, risk_free_rate
    )
    return FeasibleRange(min_volatility_result=min_vol, max_return_result=max_ret)


def generate_efficient_frontier(
    model: RiskReturnModel,
    asset_info: pd.DataFrame,
    config: ConstraintConfig,
    risk_free_rate: float,
    n_points: int = 25,
) -> pd.DataFrame:
    """Generate the upper efficient frontier from min-vol return to max return."""
    feasible = estimate_feasible_range(model, asset_info, config, risk_free_rate)
    if not feasible.min_volatility_result.success or not feasible.max_return_result.success:
        return pd.DataFrame()

    start_return = feasible.return_at_min_volatility
    end_return = feasible.max_return
    if start_return is None or end_return is None or end_return < start_return:
        return pd.DataFrame()

    target_returns = np.linspace(start_return, end_return, max(int(n_points), 2))
    rows = []
    for target in target_returns:
        result = optimize_portfolio(
            name=f"Frontier {target:.2%}",
            objective="target_return",
            model=model,
            asset_info=asset_info,
            config=config,
            risk_free_rate=risk_free_rate,
            target_return=float(target),
        )
        if result.success and result.metrics is not None:
            rows.append({
                "Target Return": float(target),
                "Annual Return": result.metrics["Annual Return"],
                "Annual Volatility": result.metrics["Annual Volatility"],
                "Sharpe Ratio": result.metrics["Sharpe Ratio"],
            })
    return pd.DataFrame(rows)
