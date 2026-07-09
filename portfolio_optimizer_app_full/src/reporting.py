from __future__ import annotations

from io import BytesIO
from datetime import datetime

import pandas as pd

from src.constraints import summarize_group_weights
from src.optimizer import OptimizationResult


PERCENT_LIKE = {
    "Annual Return",
    "Annual Volatility",
    "Sharpe Ratio",  # formatted separately as number
    "Expected Annual Return",
    "Historical Annual Return",
    "Historical Annual Volatility",
    "Target Return",
    "Weight",
    "Equity",
    "Fixed Income",
    "Cash",
    "Developed",
    "Emerging",
    "Foreign Equity",
    "Foreign Equity / Equity",
}


def build_portfolio_tables(
    results: dict[str, OptimizationResult],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build summary and weight tables from optimization results."""
    summary_rows = []
    weight_columns = []

    for name, result in results.items():
        if result.success and result.metrics is not None and result.weights is not None:
            summary_rows.append({"Portfolio": name, **result.metrics, "Status": result.message})
            weight_columns.append(result.weights.rename(name))
        else:
            summary_rows.append({
                "Portfolio": name,
                "Annual Return": pd.NA,
                "Annual Volatility": pd.NA,
                "Sharpe Ratio": pd.NA,
                "Status": result.message,
            })

    summary = pd.DataFrame(summary_rows).set_index("Portfolio")
    weights = pd.concat(weight_columns, axis=1) if weight_columns else pd.DataFrame()
    return summary, weights


def build_group_weight_table(
    weights: pd.DataFrame,
    asset_info: pd.DataFrame,
) -> pd.DataFrame:
    if weights.empty:
        return pd.DataFrame()
    rows = []
    for portfolio_name in weights.columns:
        row = {"Portfolio": portfolio_name}
        row.update(summarize_group_weights(weights[portfolio_name], asset_info))
        rows.append(row)
    return pd.DataFrame(rows).set_index("Portfolio")


def _safe_sheet_name(name: str) -> str:
    return name[:31]


def _write_df(writer, df: pd.DataFrame, sheet_name: str, index: bool = True) -> None:
    sheet_name = _safe_sheet_name(sheet_name)
    df.to_excel(writer, sheet_name=sheet_name, index=index)
    workbook = writer.book
    worksheet = writer.sheets[sheet_name]

    header_fmt = workbook.add_format({
        "bold": True,
        "font_color": "white",
        "bg_color": "#1F4E78",
        "border": 1,
        "align": "center",
        "valign": "vcenter",
    })
    pct_fmt = workbook.add_format({"num_format": "0.00%"})
    num_fmt = workbook.add_format({"num_format": "0.000"})
    text_fmt = workbook.add_format({"text_wrap": True, "valign": "top"})

    rows, cols = df.shape
    header_count = cols + (1 if index else 0)
    # Rewrite headers from the dataframe because pandas headers are easy to style but not always formatted.
    if index:
        worksheet.write(0, 0, df.index.name or "Index", header_fmt)
        for c, col_name in enumerate(df.columns, start=1):
            worksheet.write(0, c, str(col_name), header_fmt)
    else:
        for c, col_name in enumerate(df.columns):
            worksheet.write(0, c, str(col_name), header_fmt)

    worksheet.freeze_panes(1, 0)

    for c in range(header_count):
        if index and c == 0:
            values = [str(v) for v in df.index.tolist()]
            col_name = df.index.name or "Index"
        else:
            data_col = c - 1 if index else c
            col_name = str(df.columns[data_col]) if 0 <= data_col < len(df.columns) else ""
            values = [str(v) for v in df.iloc[:, data_col].tolist()] if 0 <= data_col < len(df.columns) else []
        width = min(max([len(col_name), *[len(v) for v in values[:200]]] or [10]) + 2, 36)
        fmt = text_fmt
        if col_name in PERCENT_LIKE and col_name != "Sharpe Ratio":
            fmt = pct_fmt
        elif col_name == "Sharpe Ratio":
            fmt = num_fmt
        worksheet.set_column(c, c, width, fmt)

    # Add a simple table when the sheet has data. This improves filtering and visual polish.
    if rows > 0:
        table_columns = []
        if index:
            table_columns.append({"header": df.index.name or "Index"})
        table_columns.extend({"header": str(c)} for c in df.columns)
        worksheet.add_table(0, 0, rows, header_count - 1, {
            "columns": table_columns,
            "style": "Table Style Medium 2",
            "autofilter": True,
        })


def _write_dashboard(writer, portfolio_summary: pd.DataFrame, weights: pd.DataFrame, group_weights: pd.DataFrame) -> None:
    workbook = writer.book
    worksheet = workbook.add_worksheet("Dashboard")
    writer.sheets["Dashboard"] = worksheet

    title_fmt = workbook.add_format({"bold": True, "font_size": 18, "font_color": "#1F4E78"})
    section_fmt = workbook.add_format({"bold": True, "font_size": 12, "font_color": "white", "bg_color": "#1F4E78", "border": 1})
    label_fmt = workbook.add_format({"bold": True, "border": 1, "bg_color": "#D9EAF7"})
    pct_fmt = workbook.add_format({"num_format": "0.00%", "border": 1})
    num_fmt = workbook.add_format({"num_format": "0.000", "border": 1})
    text_fmt = workbook.add_format({"border": 1})

    worksheet.write("A1", "Portfolio Optimizer Report", title_fmt)
    worksheet.write("A2", f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    worksheet.write("A4", "Key Portfolio Metrics", section_fmt)
    worksheet.write_row("A5", ["Portfolio", "Annual Return", "Annual Volatility", "Sharpe Ratio", "Status"], label_fmt)

    row = 5
    for portfolio, values in portfolio_summary.iterrows():
        worksheet.write(row, 0, str(portfolio), text_fmt)
        worksheet.write(row, 1, values.get("Annual Return"), pct_fmt)
        worksheet.write(row, 2, values.get("Annual Volatility"), pct_fmt)
        worksheet.write(row, 3, values.get("Sharpe Ratio"), num_fmt)
        worksheet.write(row, 4, str(values.get("Status", "")), text_fmt)
        row += 1

    worksheet.write("G4", "Quick Notes", section_fmt)
    notes = [
        "Use data.xlsx to change the asset universe.",
        "Asset names must match between prices and asset_info. expected_returns is optional.",
        "If expected_returns is missing or mismatched, historical returns are used.",
        "Equal Weight is a base comparison and may violate selected constraints.",
    ]
    for i, note in enumerate(notes, start=5):
        worksheet.write(i, 6, note)

    if not weights.empty:
        worksheet.write("A14", "Portfolio Weights", section_fmt)
        # Create chart from the Weights sheet after all dataframes are written.
        chart = workbook.add_chart({"type": "column"})
        for col_idx, portfolio in enumerate(weights.columns, start=1):
            chart.add_series({
                "name": ["Weights", 0, col_idx],
                "categories": ["Weights", 1, 0, len(weights), 0],
                "values": ["Weights", 1, col_idx, len(weights), col_idx],
            })
        chart.set_title({"name": "Portfolio Weights"})
        chart.set_y_axis({"num_format": "0%"})
        chart.set_legend({"position": "bottom"})
        worksheet.insert_chart("A15", chart, {"x_scale": 1.35, "y_scale": 1.2})

    if not group_weights.empty:
        chart = workbook.add_chart({"type": "column", "subtype": "stacked"})
        core_cols = [c for c in ["Equity", "Fixed Income", "Cash"] if c in group_weights.columns]
        for col_name in core_cols:
            col_idx = list(group_weights.columns).index(col_name) + 1
            chart.add_series({
                "name": ["Group Weights", 0, col_idx],
                "categories": ["Group Weights", 1, 0, len(group_weights), 0],
                "values": ["Group Weights", 1, col_idx, len(group_weights), col_idx],
            })
        chart.set_title({"name": "Asset Class Allocation"})
        chart.set_y_axis({"num_format": "0%"})
        chart.set_legend({"position": "bottom"})
        worksheet.insert_chart("G15", chart, {"x_scale": 1.35, "y_scale": 1.2})

    worksheet.set_column("A:A", 22)
    worksheet.set_column("B:D", 16)
    worksheet.set_column("E:E", 32)
    worksheet.set_column("G:G", 55)


def export_results_to_excel(
    asset_summary: pd.DataFrame,
    portfolio_summary: pd.DataFrame,
    weights: pd.DataFrame,
    group_weights: pd.DataFrame,
    covariance: pd.DataFrame,
    correlation: pd.DataFrame,
    frontier: pd.DataFrame | None = None,
    constraint_settings: pd.DataFrame | None = None,
    validation_messages: pd.DataFrame | None = None,
) -> bytes:
    """Create a polished Excel export in memory for Streamlit download."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        # Write data sheets first so dashboard charts can reference existing ranges.
        _write_df(writer, portfolio_summary, "Portfolio Summary", index=True)
        _write_df(writer, weights, "Weights", index=True)
        _write_df(writer, group_weights, "Group Weights", index=True)
        _write_df(writer, asset_summary, "Asset Summary", index=False)
        if frontier is not None and not frontier.empty:
            _write_df(writer, frontier, "Efficient Frontier", index=False)
        if constraint_settings is not None and not constraint_settings.empty:
            _write_df(writer, constraint_settings, "Constraint Settings", index=False)
        if validation_messages is not None and not validation_messages.empty:
            _write_df(writer, validation_messages, "Validation Messages", index=False)
        _write_df(writer, covariance, "Covariance", index=True)
        _write_df(writer, correlation, "Correlation", index=True)
        _write_dashboard(writer, portfolio_summary, weights, group_weights)
        writer.sheets["Dashboard"].activate()

    output.seek(0)
    return output.getvalue()
