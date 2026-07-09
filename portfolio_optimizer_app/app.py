from pathlib import Path

import pandas as pd
import streamlit as st

from src.calculations import (
    build_asset_summary,
    build_risk_return_model,
    equal_weight_series,
    portfolio_metrics,
)
from src.data_loader import load_portfolio_workbook

st.set_page_config(page_title="Portfolio Optimizer", layout="wide")

DATA_FILE = Path(__file__).with_name("data.xlsx")

st.title("Portfolio Optimizer")
st.caption("Version 0.1: data loading and risk-return calculation engine")

try:
    data = load_portfolio_workbook(DATA_FILE)
except Exception as exc:
    st.error(f"Could not load {DATA_FILE.name}: {exc}")
    st.stop()

return_method_label = st.sidebar.radio(
    "Return assumption method",
    ["Manual expected returns", "Historical returns"],
    index=0,
)
return_method = "manual_expected" if return_method_label == "Manual expected returns" else "historical"

risk_free_options = ["Use T bill expected return", "Enter manually", "Use 0%"]
risk_free_choice = st.sidebar.radio("Risk-free rate", risk_free_options, index=0)

if risk_free_choice == "Use T bill expected return" and "T bill" in data.expected_returns.index:
    risk_free_rate = float(data.expected_returns.loc["T bill"])
elif risk_free_choice == "Enter manually":
    risk_free_rate = st.sidebar.number_input(
        "Annual risk-free rate", min_value=0.0, max_value=1.0, value=0.0369, step=0.001, format="%.4f"
    )
else:
    risk_free_rate = 0.0

model = build_risk_return_model(
    prices=data.prices,
    manual_expected_annual_returns=data.expected_returns,
    return_method=return_method,
    covariance_ddof=0,
)

st.subheader("Data Summary")
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Assets", len(data.assets))
col2.metric("Price Rows", len(data.prices))
col3.metric("Return Obs.", len(model.monthly_returns))
col4.metric("Start Date", data.prices["Date"].min().strftime("%Y-%m-%d"))
col5.metric("End Date", data.prices["Date"].max().strftime("%Y-%m-%d"))

st.subheader("Asset Summary")
asset_summary = build_asset_summary(data.asset_info, model)
percent_cols = ["Expected Annual Return", "Historical Annual Return", "Historical Annual Volatility"]
st.dataframe(
    asset_summary.style.format({col: "{:.2%}" for col in percent_cols}),
    use_container_width=True,
)

st.subheader("Equal-Weight Base Portfolio")
equal_weights = equal_weight_series(data.assets)
ew_metrics = portfolio_metrics(equal_weights, model.expected_annual_returns, model.covariance_monthly, risk_free_rate)
metrics_df = pd.DataFrame([ew_metrics], index=["Equal Weight"])
st.dataframe(
    metrics_df.style.format({"Annual Return": "{:.2%}", "Annual Volatility": "{:.2%}", "Sharpe Ratio": "{:.3f}"}),
    use_container_width=True,
)

st.subheader("Monthly Covariance Matrix")
st.dataframe(model.covariance_monthly.style.format("{:.8f}"), use_container_width=True)

st.subheader("Correlation Matrix")
st.dataframe(model.correlation.style.format("{:.3f}"), use_container_width=True)
