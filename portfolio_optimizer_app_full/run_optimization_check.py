from pathlib import Path

from src.calculations import build_risk_return_model, equal_weight_series, portfolio_metrics
from src.constraints import ConstraintConfig
from src.data_loader import load_portfolio_workbook
from src.frontier import generate_efficient_frontier
from src.optimizer import OptimizationResult, optimize_portfolio
from src.reporting import build_group_weight_table, build_portfolio_tables

DATA_FILE = Path(__file__).with_name("data.xlsx")


def pct(x: float) -> str:
    return f"{x:.4%}"


def main() -> None:
    data = load_portfolio_workbook(DATA_FILE)
    model = build_risk_return_model(
        prices=data.prices,
        manual_expected_annual_returns=data.expected_returns,
        return_method="manual_expected",
        covariance_ddof=0,
    )
    risk_free_rate = float(model.expected_annual_returns.loc["T bill"])

    config = ConstraintConfig(
        no_short=True,
        equity_min=0.60,
        equity_max=0.80,
        fixed_income_min=0.20,
        fixed_income_max=0.40,
        cash_max=0.20,
        foreign_equity_max_pct_of_equity=0.50,
    )

    results = {}
    equal_weights = equal_weight_series(data.assets)
    results["Equal Weight"] = OptimizationResult(
        name="Equal Weight",
        success=True,
        message="Base comparison portfolio. Constraints are not enforced.",
        weights=equal_weights,
        metrics=portfolio_metrics(equal_weights, model.expected_annual_returns, model.covariance_monthly, risk_free_rate),
    )
    for name, objective in [
        ("Max Return", "max_return"),
        ("Min Volatility", "min_volatility"),
        ("Max Sharpe", "max_sharpe"),
    ]:
        results[name] = optimize_portfolio(name, objective, model, data.asset_info, config, risk_free_rate)

    results["Target Return 7%"] = optimize_portfolio(
        "Target Return 7%",
        "target_return",
        model,
        data.asset_info,
        config,
        risk_free_rate,
        target_return=0.07,
    )
    results["Target Risk 10%"] = optimize_portfolio(
        "Target Risk 10%",
        "target_risk",
        model,
        data.asset_info,
        config,
        risk_free_rate,
        target_risk=0.10,
    )

    summary, weights = build_portfolio_tables(results)
    group_weights = build_group_weight_table(weights, data.asset_info)
    frontier = generate_efficient_frontier(model, data.asset_info, config, risk_free_rate, n_points=10)

    print("Portfolio Summary")
    print("-----------------")
    print(summary.to_string(formatters={
        "Annual Return": pct,
        "Annual Volatility": pct,
        "Sharpe Ratio": lambda x: f"{x:.4f}",
    }))

    print("\nWeights")
    print("-------")
    print(weights.to_string(formatters={col: pct for col in weights.columns}))

    print("\nGroup Weights")
    print("-------------")
    print(group_weights.to_string(formatters={col: pct for col in group_weights.columns}))

    print("\nEfficient Frontier")
    print("------------------")
    print(frontier.to_string(index=False, formatters={
        "Target Return": pct,
        "Annual Return": pct,
        "Annual Volatility": pct,
        "Sharpe Ratio": lambda x: f"{x:.4f}",
    }))


if __name__ == "__main__":
    main()
