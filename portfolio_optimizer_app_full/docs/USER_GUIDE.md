# User Guide

## 1. Prepare the input workbook

You can either use the included sample data or upload your own workbook. For a shared Streamlit link, click **Download Excel template** in the sidebar, fill in the workbook, then upload it back into the app.

The workbook must contain:

- `prices`: `Date` plus one column per asset with price or index levels
- `asset_info`: `Asset`, `Asset Class`, `Region`, `Subgroup`

Optional sheets:

- `expected_returns`: `Asset`, `Expected Annual Return`
- `classification_guide`: reference sheet that explains how to classify assets

Asset names must match exactly between `prices` and `asset_info`. If you use manual expected returns, asset names in `expected_returns` should also match exactly. If the expected return sheet is missing, blank, incomplete, or mismatched, the app automatically uses historical returns.

## 2. Load data in the app

In the sidebar, choose one of two options:

- **Use included sample data**: runs the built-in `data.xlsx` or `sample_data.xlsx`.
- **Upload my own Excel file**: lets each user upload their completed template through the browser.

The upload workflow is best for a public Streamlit deployment because each user can run their own data without changing the project files.

## 3. Run the app locally

Windows:

```bash
py -m streamlit run app.py
```

Or double-click `run_app.bat`.

Mac/Linux:

```bash
python -m streamlit run app.py
```

Or run:

```bash
./run_app.sh
```

## 4. Select assumptions

Choose either:

- Manual expected returns: uses the `expected_returns` sheet when it is complete and matched
- Historical returns: calculates annualized expected returns from the price history. This is also the automatic fallback when manual expected returns are unavailable

Then select the risk-free rate:

- Use T bill return assumption
- Enter manually
- Use 0%

## 5. Select constraints

Choose a constraint preset, then adjust values in the sidebar. If a constraint is not selected, the optimizer ignores it.

Built-in constraints include:

- No short selling
- Individual asset min/max
- Equity min/max
- Fixed income min/max
- Cash min/max
- Developed min/max
- Emerging min/max
- Foreign equity max as a percentage of total equity

## 6. Run optimizations

The app can run:

- Equal Weight
- Max Return
- Min Volatility
- Max Sharpe
- Target Return
- Target Risk
- Efficient Frontier

## 7. Export results

After optimization, open the `Export` tab and download the polished Excel report. It includes a dashboard, summary tables, weights, group weights, asset summary, efficient frontier data, covariance, correlation, constraint settings and validation messages.


## Auto-populating asset names in the template

Use the sidebar button to download `portfolio_optimizer_template.xlsx`. When you change the asset headers in the `prices` sheet, the `Asset` columns in `asset_info` and `expected_returns` update automatically. You still need to fill the classification fields manually.

Save the workbook after editing, then upload it back into the app.
