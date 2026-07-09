from pathlib import Path

import pandas as pd

from src.calculations import (
    build_asset_summary,
    build_risk_return_model,
    equal_weight_series,
    portfolio_metrics,
)
from src.data_loader import load_portfolio_workbook

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

    risk_free_rate = float(data.expected_returns.loc["T bill"])
    equal_weights = equal_weight_series(data.assets)
    ew_metrics = portfolio_metrics(
        equal_weights,
        model.expected_annual_returns,
        model.covariance_monthly,
        risk_free_rate,
    )

    print("Input data summary")
    print("------------------")
    print(f"Assets: {len(data.assets)}")
    print(f"Price rows: {len(data.prices)}")
    print(f"Monthly return observations: {len(model.monthly_returns)}")
    print(f"Start date: {data.prices['Date'].min().date()}")
    print(f"End date: {data.prices['Date'].max().date()}")
    print(f"Risk-free rate: {pct(risk_free_rate)}")

    print("\nEqual-weight portfolio using standard Sharpe ratio")
    print("-------------------------------------------------")
    for key, value in ew_metrics.items():
        print(f"{key}: {pct(value) if key != 'Sharpe Ratio' else f'{value:.4f}'}")

    print("\nAsset summary")
    print("-------------")
    asset_summary = build_asset_summary(data.asset_info, model)
    display_cols = [
        "Asset",
        "Asset Class",
        "Region",
        "Subgroup",
        "Expected Annual Return",
        "Historical Annual Return",
        "Historical Annual Volatility",
    ]
    print(asset_summary[display_cols].to_string(index=False, formatters={
        "Expected Annual Return": pct,
        "Historical Annual Return": pct,
        "Historical Annual Volatility": pct,
    }))

    print("\nMonthly covariance matrix")
    print("-------------------------")
    print(model.covariance_monthly.round(8).to_string())


if __name__ == "__main__":
    main()
