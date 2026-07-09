from pathlib import Path

from src.calculations import build_risk_return_model
from src.constraints import ConstraintConfig
from src.data_loader import load_portfolio_workbook
from src.validation import validate_constraint_config, validate_risk_return_model

DATA_FILE = Path(__file__).with_name("data.xlsx")


def print_report(title: str, errors: list[str], warnings: list[str]) -> None:
    print(title)
    print("-" * len(title))
    if not errors and not warnings:
        print("No errors or warnings.")
    for error in errors:
        print(f"ERROR: {error}")
    for warning in warnings:
        print(f"WARNING: {warning}")
    print()


def main() -> None:
    data = load_portfolio_workbook(DATA_FILE)
    model = build_risk_return_model(
        prices=data.prices,
        manual_expected_annual_returns=data.expected_returns,
        return_method="manual_expected",
        covariance_ddof=0,
    )
    config = ConstraintConfig(
        no_short=True,
        equity_min=0.60,
        equity_max=0.80,
        fixed_income_min=0.20,
        fixed_income_max=0.40,
        cash_max=0.20,
        foreign_equity_max_pct_of_equity=0.50,
    )

    model_report = validate_risk_return_model(model)
    constraint_report = validate_constraint_config(data.asset_info, config)

    print_report("Workbook warnings", [], data.validation_warnings)
    print_report("Risk-return model validation", model_report.errors, model_report.warnings)
    print_report("Constraint validation", constraint_report.errors, constraint_report.warnings)


if __name__ == "__main__":
    main()
