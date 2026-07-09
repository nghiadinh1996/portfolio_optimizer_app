from pathlib import Path

from src.calculations import build_asset_summary, build_risk_return_model, equal_weight_series, portfolio_metrics
from src.constraints import ConstraintConfig
from src.data_loader import load_portfolio_workbook
from src.frontier import generate_efficient_frontier
from src.optimizer import OptimizationResult, optimize_portfolio
from src.reporting import build_group_weight_table, build_portfolio_tables, export_results_to_excel
from src.validation import build_constraint_settings_table

DATA_FILE = Path(__file__).with_name("data.xlsx")


def main() -> None:
    data = load_portfolio_workbook(DATA_FILE)
    model = build_risk_return_model(data.prices, data.expected_returns, return_method="manual_expected", covariance_ddof=0)
    risk_free_rate = float(model.expected_annual_returns.loc["T bill"])
    config = ConstraintConfig(no_short=True, equity_min=0.60, equity_max=0.80, fixed_income_min=0.20, fixed_income_max=0.40, cash_max=0.20, foreign_equity_max_pct_of_equity=0.50)
    results = {}
    ew = equal_weight_series(data.assets)
    results["Equal Weight"] = OptimizationResult("Equal Weight", True, "Base comparison portfolio. Constraints are not enforced.", ew, portfolio_metrics(ew, model.expected_annual_returns, model.covariance_monthly, risk_free_rate))
    for name, obj in [("Max Return", "max_return"), ("Min Volatility", "min_volatility"), ("Max Sharpe", "max_sharpe")]:
        results[name] = optimize_portfolio(name, obj, model, data.asset_info, config, risk_free_rate)
    summary, weights = build_portfolio_tables(results)
    groups = build_group_weight_table(weights, data.asset_info)
    frontier = generate_efficient_frontier(model, data.asset_info, config, risk_free_rate, n_points=12)
    asset_summary = build_asset_summary(data.asset_info, model)
    excel = export_results_to_excel(asset_summary, summary, weights, groups, model.covariance_monthly, model.correlation, frontier, build_constraint_settings_table(config))
    out = Path(__file__).with_name("output")
    out.mkdir(exist_ok=True)
    report = out / "optimization_results_check.xlsx"
    report.write_bytes(excel)
    print(f"Full check completed. Excel bytes: {len(excel):,}. Report: {report}")
    print(summary.round(4).to_string())


if __name__ == "__main__":
    main()
