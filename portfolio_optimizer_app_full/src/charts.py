from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


DEFAULT_LAYOUT = {
    "template": "plotly_white",
    "legend": {"orientation": "h", "yanchor": "bottom", "y": -0.25, "xanchor": "center", "x": 0.5},
    "margin": {"l": 30, "r": 30, "t": 60, "b": 80},
}


def _apply_layout(fig: go.Figure, title: str) -> go.Figure:
    fig.update_layout(title=title, **DEFAULT_LAYOUT)
    return fig


def weight_bar_chart(weights: pd.DataFrame):
    if weights.empty:
        return None
    plot_df = weights.reset_index().melt(id_vars="index", var_name="Portfolio", value_name="Weight")
    plot_df = plot_df.rename(columns={"index": "Asset"})
    fig = px.bar(plot_df, x="Asset", y="Weight", color="Portfolio", barmode="group")
    fig.update_yaxes(tickformat=".0%", title="Weight")
    fig.update_xaxes(title="Asset")
    return _apply_layout(fig, "Portfolio Weights by Asset")


def stacked_weight_chart(weights: pd.DataFrame):
    if weights.empty:
        return None
    plot_df = weights.T.reset_index().rename(columns={"index": "Portfolio"})
    plot_df = plot_df.melt(id_vars="Portfolio", var_name="Asset", value_name="Weight")
    fig = px.bar(plot_df, x="Portfolio", y="Weight", color="Asset")
    fig.update_yaxes(tickformat=".0%", title="Total Weight")
    fig.update_xaxes(title="Portfolio")
    return _apply_layout(fig, "Stacked Portfolio Allocation")


def group_allocation_chart(group_weights: pd.DataFrame):
    if group_weights.empty:
        return None
    core_cols = [c for c in ["Equity", "Fixed Income", "Cash"] if c in group_weights.columns]
    if not core_cols:
        return None
    plot_df = group_weights[core_cols].reset_index().melt(
        id_vars="Portfolio", var_name="Group", value_name="Weight"
    )
    fig = px.bar(plot_df, x="Portfolio", y="Weight", color="Group")
    fig.update_yaxes(tickformat=".0%", title="Total Weight")
    fig.update_xaxes(title="Portfolio")
    return _apply_layout(fig, "Asset Class Allocation")


def metric_comparison_chart(portfolio_summary: pd.DataFrame):
    if portfolio_summary.empty:
        return None
    metric_cols = [c for c in ["Annual Return", "Annual Volatility", "Sharpe Ratio"] if c in portfolio_summary.columns]
    if not metric_cols:
        return None
    plot_df = portfolio_summary.reset_index().melt(
        id_vars="Portfolio", value_vars=metric_cols, var_name="Metric", value_name="Value"
    )
    fig = px.bar(plot_df, x="Portfolio", y="Value", color="Metric", barmode="group")
    fig.update_yaxes(title="Value")
    fig.update_xaxes(title="Portfolio")
    return _apply_layout(fig, "Portfolio Metric Comparison")


def risk_return_chart(portfolio_summary: pd.DataFrame, frontier: pd.DataFrame | None = None):
    if portfolio_summary.empty:
        return None
    fig = go.Figure()

    if frontier is not None and not frontier.empty:
        fig.add_trace(go.Scatter(
            x=frontier["Annual Volatility"],
            y=frontier["Annual Return"],
            mode="lines+markers",
            marker={"size": 5},
            line={"width": 2},
            name="Efficient Frontier",
            hovertemplate="Risk: %{x:.2%}<br>Return: %{y:.2%}<br>Sharpe: %{customdata:.3f}<extra></extra>",
            customdata=frontier["Sharpe Ratio"],
        ))

    summary = portfolio_summary.dropna(subset=["Annual Return", "Annual Volatility"]).reset_index()
    if not summary.empty:
        fig.add_trace(go.Scatter(
            x=summary["Annual Volatility"],
            y=summary["Annual Return"],
            mode="markers+text",
            marker={"size": 12, "symbol": "diamond"},
            text=summary["Portfolio"],
            textposition="top center",
            name="Selected Portfolios",
            hovertemplate="%{text}<br>Risk: %{x:.2%}<br>Return: %{y:.2%}<br>Sharpe: %{customdata:.3f}<extra></extra>",
            customdata=summary["Sharpe Ratio"],
        ))

    fig.update_xaxes(tickformat=".1%", title="Annual Volatility")
    fig.update_yaxes(tickformat=".1%", title="Annual Return")
    return _apply_layout(fig, "Risk-Return Profile and Efficient Frontier")


def correlation_heatmap(correlation: pd.DataFrame):
    fig = px.imshow(
        correlation,
        text_auto=".2f",
        aspect="auto",
        title="Correlation Matrix",
        zmin=-1,
        zmax=1,
        color_continuous_scale="RdBu_r",
    )
    fig.update_layout(template="plotly_white", margin={"l": 30, "r": 30, "t": 60, "b": 30})
    return fig
