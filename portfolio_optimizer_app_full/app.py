from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from src.calculations import (
    build_asset_summary,
    build_risk_return_model,
    equal_weight_series,
    portfolio_metrics,
)
from src.charts import (
    correlation_heatmap,
    group_allocation_chart,
    metric_comparison_chart,
    risk_return_chart,
    stacked_weight_chart,
    weight_bar_chart,
)
from src.constraints import ConstraintConfig
from src.data_loader import load_portfolio_workbook
from src.frontier import estimate_feasible_range, generate_efficient_frontier
from src.optimizer import OptimizationResult, optimize_portfolio
from src.presets import config_to_dict, load_presets, save_presets
from src.reporting import build_group_weight_table, build_portfolio_tables, export_results_to_excel
from src.validation import (
    build_constraint_settings_table,
    validate_constraint_config,
    validate_risk_return_model,
)

st.set_page_config(page_title="Portfolio Optimizer", layout="wide")

APP_DIR = Path(__file__).resolve().parent
DATA_FILE = APP_DIR / "data.xlsx"
SAMPLE_FILE = APP_DIR / "sample_data.xlsx"
TEMPLATE_FILE = APP_DIR / "portfolio_optimizer_template.xlsx"
PRESET_FILE = APP_DIR / "presets.json"


def pct_display(value: float | None) -> str:
    return "Off" if value is None else f"{value:.2%}"


def pct_number_input(label: str, value: float | None, step: float = 1.0, max_value: float = 100.0) -> float:
    default = 0.0 if value is None else float(value) * 100
    return st.sidebar.number_input(label, min_value=0.0, max_value=max_value, value=float(default), step=step, format="%.2f") / 100


def optional_min_max(prefix: str, default_min: float | None, default_max: float | None) -> tuple[float | None, float | None]:
    active_default = default_min is not None or default_max is not None
    active = st.sidebar.checkbox(f"Use {prefix} min/max", value=active_default)
    if not active:
        return None, None
    c1, c2 = st.sidebar.columns(2)
    min_default = 0.0 if default_min is None else default_min * 100
    max_default = 100.0 if default_max is None else default_max * 100
    min_v = c1.number_input(f"{prefix} min %", min_value=0.0, max_value=100.0, value=float(min_default), step=1.0, format="%.2f") / 100
    max_v = c2.number_input(f"{prefix} max %", min_value=0.0, max_value=100.0, value=float(max_default), step=1.0, format="%.2f") / 100
    return min_v, max_v


def validation_messages_dataframe(errors: list[str], warnings: list[str]) -> pd.DataFrame:
    rows = []
    rows.extend({"Type": "Error", "Message": msg} for msg in errors)
    rows.extend({"Type": "Warning", "Message": msg} for msg in warnings)
    return pd.DataFrame(rows)


def run_optimizer_workflow(
    data,
    model,
    config: ConstraintConfig,
    risk_free_rate: float,
    run_equal: bool,
    run_max_return: bool,
    run_min_volatility: bool,
    run_max_sharpe: bool,
    run_target_return: bool,
    target_return: float | None,
    run_target_risk: bool,
    target_risk: float | None,
    run_frontier: bool,
    frontier_points: int,
) -> tuple[dict[str, OptimizationResult], pd.DataFrame, object]:
    results: dict[str, OptimizationResult] = {}
    frontier_df = pd.DataFrame()

    feasible = estimate_feasible_range(model, data.asset_info, config, risk_free_rate)
    if not feasible.min_volatility_result.success or not feasible.max_return_result.success:
        return {
            "Feasibility Check": OptimizationResult(
                name="Feasibility Check",
                success=False,
                message=(
                    "Selected constraints appear infeasible. "
                    f"Min Vol status: {feasible.min_volatility_result.message}; "
                    f"Max Return status: {feasible.max_return_result.message}"
                ),
                weights=None,
                metrics=None,
            )
        }, frontier_df, feasible

    if run_equal:
        equal_weights = equal_weight_series(data.assets)
        results["Equal Weight"] = OptimizationResult(
            name="Equal Weight",
            success=True,
            message="Base comparison portfolio. Constraints are not enforced.",
            weights=equal_weights,
            metrics=portfolio_metrics(equal_weights, model.expected_annual_returns, model.covariance_monthly, risk_free_rate),
        )

    if run_max_return:
        results["Max Return"] = feasible.max_return_result
    if run_min_volatility:
        results["Min Volatility"] = feasible.min_volatility_result
    if run_max_sharpe:
        results["Max Sharpe"] = optimize_portfolio("Max Sharpe", "max_sharpe", model, data.asset_info, config, risk_free_rate)

    if run_target_return and target_return is not None:
        max_feasible_return = feasible.max_return
        if max_feasible_return is not None and target_return > max_feasible_return + 1e-6:
            results["Target Return"] = OptimizationResult(
                name="Target Return",
                success=False,
                message=f"Target return is infeasible. Max feasible return is about {max_feasible_return:.2%}.",
                weights=None,
                metrics=None,
            )
        else:
            results["Target Return"] = optimize_portfolio(
                "Target Return", "target_return", model, data.asset_info, config, risk_free_rate, target_return=target_return
            )

    if run_target_risk and target_risk is not None:
        min_feasible_risk = feasible.min_volatility
        if min_feasible_risk is not None and target_risk < min_feasible_risk - 1e-6:
            results["Target Risk"] = OptimizationResult(
                name="Target Risk",
                success=False,
                message=f"Target risk is infeasible. Min feasible volatility is about {min_feasible_risk:.2%}.",
                weights=None,
                metrics=None,
            )
        else:
            results["Target Risk"] = optimize_portfolio(
                "Target Risk", "target_risk", model, data.asset_info, config, risk_free_rate, target_risk=target_risk
            )

    if run_frontier:
        frontier_df = generate_efficient_frontier(model, data.asset_info, config, risk_free_rate, n_points=frontier_points)

    return results, frontier_df, feasible


st.title("Portfolio Optimizer")
st.caption("Version 1.3: auto-populating Excel template plus optional expected-return fallback")

# Sidebar: data source
st.sidebar.header("0. Data Source")
template_path = TEMPLATE_FILE if TEMPLATE_FILE.exists() else (SAMPLE_FILE if SAMPLE_FILE.exists() else DATA_FILE)
if template_path.exists():
    with open(template_path, "rb") as template_file:
        st.sidebar.download_button(
            "Download Excel template",
            data=template_file,
            file_name="portfolio_optimizer_template.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            help="Download this template. Asset names in asset_info and expected_returns auto-populate from prices, but classifications still need to be reviewed.",
        )
else:
    st.sidebar.warning("No template workbook was found in the app folder.")

data_source_choice = st.sidebar.radio(
    "Choose input data",
    ["Use included sample data", "Upload my own Excel file"],
    index=0,
)

uploaded_file = None
if data_source_choice == "Upload my own Excel file":
    uploaded_file = st.sidebar.file_uploader(
        "Upload completed Excel workbook",
        type=["xlsx"],
        help="The workbook must include prices and asset_info. expected_returns is optional.",
    )
    if uploaded_file is None:
        st.info("Download the Excel template from the sidebar, fill it in, then upload the completed .xlsx file to run your own data.")
        with st.expander("Expected workbook structure", expanded=True):
            st.markdown(
                """
                Required sheets:
                - `prices`: `Date` plus one column per asset with price/index levels
                - `asset_info`: `Asset`, `Asset Class`, `Region`, `Subgroup`

                Template behavior:
                - `asset_info` column A auto-populates from the asset headers in `prices`
                - `expected_returns` column A also auto-populates from the asset headers in `prices`
                - You still need to review/fill `Asset Class`, `Region`, and `Subgroup` manually

                Optional sheets:
                - `expected_returns`: `Asset`, `Expected Annual Return`
                - `classification_guide`: reference sheet explaining the classification fields

                If `expected_returns` is missing, incomplete, or mismatched, the app automatically uses historical returns.
                If used, expected returns should be entered as Excel percentages, such as `8.97%`, or as decimals, such as `0.0897`.
                Save the workbook after editing so Excel stores the updated auto-filled asset names.
                """
            )
        st.stop()
    workbook_source = uploaded_file
    workbook_name = uploaded_file.name
else:
    workbook_source = DATA_FILE if DATA_FILE.exists() else SAMPLE_FILE
    workbook_name = Path(workbook_source).name

try:
    data = load_portfolio_workbook(workbook_source)
except Exception as exc:
    st.error(f"Could not load workbook: {workbook_name}")
    st.write(str(exc))
    with st.expander("Expected workbook structure"):
        st.markdown(
            """
            Required sheets:
            - `prices`: `Date` plus one column per asset with price/index levels
            - `asset_info`: `Asset`, `Asset Class`, `Region`, `Subgroup`

            Optional sheets:
            - `expected_returns`: `Asset`, `Expected Annual Return`
            - `classification_guide`: reference sheet explaining the classification fields

            If `expected_returns` is missing, incomplete, or mismatched, the app automatically uses historical returns.
            If used, expected returns should be entered as Excel percentages, such as `8.97%`, or as decimals, such as `0.0897`.
            Do not enter `8.97`, because Python reads that as 897%.
            """
        )
    st.stop()

# Sidebar: return assumption method
st.sidebar.header("1. Assumptions")
manual_available = bool(getattr(data, "expected_returns_available", False))
default_return_index = 0 if manual_available else 1
return_method_label = st.sidebar.radio("Return assumption method", ["Manual expected returns", "Historical returns"], index=default_return_index)
return_method = "manual_expected" if return_method_label == "Manual expected returns" else "historical"

if return_method == "manual_expected" and not manual_available:
    st.sidebar.warning("Manual expected returns are unavailable for this workbook. Using historical returns instead.")
    return_method = "historical"
    return_method_label = "Historical returns (auto fallback)"

try:
    model = build_risk_return_model(
        prices=data.prices,
        manual_expected_annual_returns=data.expected_returns,
        return_method=return_method,
        covariance_ddof=0,
    )
except Exception as exc:
    st.error("Could not build the risk-return model.")
    st.write(str(exc))
    st.stop()

model_report = validate_risk_return_model(model)
if model_report.errors:
    st.error("The risk-return model has validation error(s).")
    for error in model_report.errors:
        st.write(f"- {error}")
    st.stop()

risk_free_options = ["Use T bill return assumption", "Enter manually", "Use 0%"]
rf_default_index = 0 if "T bill" in model.expected_annual_returns.index else 1
risk_free_choice = st.sidebar.radio("Risk-free rate", risk_free_options, index=rf_default_index)

if risk_free_choice == "Use T bill return assumption" and "T bill" in model.expected_annual_returns.index:
    risk_free_rate = float(model.expected_annual_returns.loc["T bill"])
elif risk_free_choice == "Enter manually":
    risk_free_rate = st.sidebar.number_input("Annual risk-free rate %", min_value=0.0, max_value=100.0, value=3.69, step=0.10, format="%.2f") / 100
else:
    risk_free_rate = 0.0

# Sidebar: presets and constraints
st.sidebar.header("2. Constraints")
presets = load_presets(PRESET_FILE)
preset_name = st.sidebar.selectbox("Constraint preset", list(presets.keys()), index=0)
preset = presets[preset_name]
st.sidebar.caption("Select a preset, then edit individual values below. Inactive constraints are ignored.")

no_short = st.sidebar.checkbox("No short selling", value=bool(preset.get("no_short", True)))

use_individual_min = st.sidebar.checkbox("Use individual asset min", value=preset.get("individual_min") is not None)
individual_min = pct_number_input("Individual asset min %", preset.get("individual_min"), step=1.0) if use_individual_min else None

use_individual_max = st.sidebar.checkbox("Use individual asset max", value=preset.get("individual_max") is not None)
individual_max = pct_number_input("Individual asset max %", preset.get("individual_max"), step=1.0) if use_individual_max else None

equity_min, equity_max = optional_min_max("Equity", preset.get("equity_min"), preset.get("equity_max"))
fixed_income_min, fixed_income_max = optional_min_max("Fixed income", preset.get("fixed_income_min"), preset.get("fixed_income_max"))
cash_min, cash_max = optional_min_max("Cash", preset.get("cash_min"), preset.get("cash_max"))
developed_min, developed_max = optional_min_max("Developed", preset.get("developed_min"), preset.get("developed_max"))
emerging_min, emerging_max = optional_min_max("Emerging", preset.get("emerging_min"), preset.get("emerging_max"))

use_foreign_equity = st.sidebar.checkbox(
    "Use foreign equity max as % of equity",
    value=preset.get("foreign_equity_max_pct_of_equity") is not None,
)
foreign_equity_max = pct_number_input(
    "Foreign equity max / equity %", (preset.get("foreign_equity_max_pct_of_equity") or 0.50), step=5.0
) if use_foreign_equity else None

config = ConstraintConfig(
    no_short=no_short,
    individual_min=individual_min,
    individual_max=individual_max,
    equity_min=equity_min,
    equity_max=equity_max,
    fixed_income_min=fixed_income_min,
    fixed_income_max=fixed_income_max,
    cash_min=cash_min,
    cash_max=cash_max,
    developed_min=developed_min,
    developed_max=developed_max,
    emerging_min=emerging_min,
    emerging_max=emerging_max,
    foreign_equity_max_pct_of_equity=foreign_equity_max,
)

with st.sidebar.expander("Save current constraints as preset"):
    new_preset_name = st.text_input("New preset name")
    if st.button("Save preset"):
        if not new_preset_name.strip():
            st.warning("Enter a preset name first.")
        else:
            presets[new_preset_name.strip()] = config_to_dict(config)
            save_presets(PRESET_FILE, presets)
            st.success(f"Saved preset: {new_preset_name.strip()}")

constraint_report = validate_constraint_config(data.asset_info, config)
constraint_settings = build_constraint_settings_table(config)

# Sidebar: optimization choices
st.sidebar.header("3. Optimization outputs")
run_equal = st.sidebar.checkbox("Equal Weight", value=True)
run_max_return = st.sidebar.checkbox("Max Return", value=True)
run_min_volatility = st.sidebar.checkbox("Min Volatility", value=True)
run_max_sharpe = st.sidebar.checkbox("Max Sharpe", value=True)
run_target_return = st.sidebar.checkbox("Target Return", value=False)
target_return = pct_number_input("Target annual return %", 0.07, step=0.25) if run_target_return else None
run_target_risk = st.sidebar.checkbox("Target Risk", value=False)
target_risk = pct_number_input("Target annual volatility %", 0.10, step=0.25) if run_target_risk else None
run_frontier = st.sidebar.checkbox("Efficient Frontier", value=True)
frontier_points = st.sidebar.slider("Frontier portfolios", min_value=10, max_value=100, value=40, step=5)
run_button = st.sidebar.button("Run optimization", type="primary")

# Pre-run dashboard
summary_tab, assumptions_tab, diagnostics_tab = st.tabs(["Data Preview", "Assumptions & Constraints", "Diagnostics"])
with summary_tab:
    st.caption(f"Input workbook: `{workbook_name}`")
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Assets", len(data.assets))
    c2.metric("Price Rows", len(data.prices))
    c3.metric("Return Obs.", len(model.monthly_returns))
    c4.metric("Start Date", data.prices["Date"].min().strftime("%Y-%m-%d"))
    c5.metric("End Date", data.prices["Date"].max().strftime("%Y-%m-%d"))
    c6.metric("Risk-Free Rate", f"{risk_free_rate:.2%}")

    asset_summary = build_asset_summary(data.asset_info, model)
    percent_cols = ["Expected Annual Return", "Historical Annual Return", "Historical Annual Volatility"]
    st.dataframe(asset_summary.style.format({col: "{:.2%}" for col in percent_cols}), use_container_width=True)

with assumptions_tab:
    a1, a2 = st.columns(2)
    with a1:
        st.markdown("**Selected Method**")
        st.write(f"Return assumption: `{return_method_label}`")
        st.write(f"Manual expected returns available: `{manual_available}`")
        st.write(f"Risk-free rate: `{risk_free_rate:.2%}`")
        st.write(f"Preset source: `{preset_name}`")
    with a2:
        st.markdown("**Active Constraint Settings**")
        st.dataframe(constraint_settings, use_container_width=True)

    if constraint_report.errors:
        st.error("The selected constraints have error(s). Fix them before running optimization.")
        for error in constraint_report.errors:
            st.write(f"- {error}")
    if constraint_report.warnings:
        st.warning("The selected constraints have warning(s). Review before running optimization.")
        for warning in constraint_report.warnings:
            st.write(f"- {warning}")

with diagnostics_tab:
    if data.validation_warnings or model_report.warnings:
        for warning in data.validation_warnings + model_report.warnings:
            st.warning(warning)
    else:
        st.success("No input or model warnings detected.")
    with st.expander("Monthly Covariance Matrix"):
        st.dataframe(model.covariance_monthly.style.format("{:.8f}"), use_container_width=True)
    with st.expander("Correlation Matrix"):
        st.plotly_chart(correlation_heatmap(model.correlation), use_container_width=True)
        st.dataframe(model.correlation.style.format("{:.3f}"), use_container_width=True)

if not run_button:
    st.info("Choose constraints and optimization outputs in the sidebar, then click **Run optimization**.")
    st.stop()
if constraint_report.errors:
    st.stop()

with st.spinner("Running optimization..."):
    results, frontier_df, feasible = run_optimizer_workflow(
        data=data,
        model=model,
        config=config,
        risk_free_rate=risk_free_rate,
        run_equal=run_equal,
        run_max_return=run_max_return,
        run_min_volatility=run_min_volatility,
        run_max_sharpe=run_max_sharpe,
        run_target_return=run_target_return,
        target_return=target_return,
        run_target_risk=run_target_risk,
        target_risk=target_risk,
        run_frontier=run_frontier,
        frontier_points=frontier_points,
    )

if "Feasibility Check" in results and not results["Feasibility Check"].success:
    st.error(results["Feasibility Check"].message)
    st.stop()

portfolio_summary, weights = build_portfolio_tables(results)
group_weights = build_group_weight_table(weights, data.asset_info)
failed = {name: res for name, res in results.items() if not res.success}

results_tab, charts_tab, frontier_tab, export_tab = st.tabs(["Results", "Charts", "Efficient Frontier", "Export"])

with results_tab:
    st.subheader("Feasible Range Under Selected Constraints")
    fc1, fc2, fc3 = st.columns(3)
    fc1.metric("Minimum Feasible Volatility", f"{feasible.min_volatility:.2%}")
    fc2.metric("Return at Min Volatility", f"{feasible.return_at_min_volatility:.2%}")
    fc3.metric("Maximum Feasible Return", f"{feasible.max_return:.2%}")

    if failed:
        st.warning("Some requested optimizations were infeasible or did not converge.")
        for name, res in failed.items():
            st.write(f"**{name}:** {res.message}")

    st.subheader("Portfolio Summary")
    st.dataframe(
        portfolio_summary.style.format({"Annual Return": "{:.2%}", "Annual Volatility": "{:.2%}", "Sharpe Ratio": "{:.3f}"}, na_rep=""),
        use_container_width=True,
    )
    st.subheader("Portfolio Weights")
    st.dataframe(weights.style.format("{:.2%}"), use_container_width=True)
    st.subheader("Group Weights")
    st.dataframe(group_weights.style.format("{:.2%}"), use_container_width=True)

with charts_tab:
    rr_fig = risk_return_chart(portfolio_summary, frontier_df)
    if rr_fig is not None:
        st.plotly_chart(rr_fig, use_container_width=True)
    c1, c2 = st.columns(2)
    with c1:
        fig = group_allocation_chart(group_weights)
        if fig is not None:
            st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig = metric_comparison_chart(portfolio_summary)
        if fig is not None:
            st.plotly_chart(fig, use_container_width=True)
    fig = stacked_weight_chart(weights)
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True)
    with st.expander("Detailed asset weight chart"):
        fig = weight_bar_chart(weights)
        if fig is not None:
            st.plotly_chart(fig, use_container_width=True)

with frontier_tab:
    if not run_frontier:
        st.info("Efficient Frontier was not selected.")
    elif frontier_df.empty:
        st.warning("No efficient frontier points were generated. The constraints may be too tight.")
    else:
        st.dataframe(
            frontier_df.style.format({"Target Return": "{:.2%}", "Annual Return": "{:.2%}", "Annual Volatility": "{:.2%}", "Sharpe Ratio": "{:.3f}"}),
            use_container_width=True,
        )

with export_tab:
    validation_df = validation_messages_dataframe(
        errors=[],
        warnings=data.validation_warnings + model_report.warnings + constraint_report.warnings,
    )
    excel_bytes = export_results_to_excel(
        asset_summary=asset_summary,
        portfolio_summary=portfolio_summary,
        weights=weights,
        group_weights=group_weights,
        covariance=model.covariance_monthly,
        correlation=model.correlation,
        frontier=frontier_df,
        constraint_settings=constraint_settings,
        validation_messages=validation_df,
    )
    st.download_button(
        "Download polished Excel report",
        data=excel_bytes,
        file_name="optimization_results.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    st.markdown(
        """
        The Excel report includes a Dashboard sheet, portfolio summary, weights, group weights, asset summary,
        efficient frontier data, covariance, correlation, constraint settings and validation messages.
        """
    )
