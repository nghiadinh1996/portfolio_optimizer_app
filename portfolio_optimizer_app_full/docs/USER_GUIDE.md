# User Guide

## 1. Prepare `data.xlsx`

Keep the workbook in the same folder as `app.py`. The workbook must contain:

- `prices`: `Date` plus one column per asset with price or index levels
- `asset_info`: `Asset`, `Asset Class`, `Region`, `Subgroup`
- `expected_returns`: `Asset`, `Expected Annual Return`
- `classification_guide`: optional reference sheet that explains how to classify assets

Asset names must match exactly across `prices`, `asset_info` and `expected_returns`.

## 2. Run the app

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

## 3. Select assumptions

Choose either:

- Manual expected returns: uses the `expected_returns` sheet
- Historical returns: calculates annualized expected returns from the price history

Then select the risk-free rate:

- Use T bill return assumption
- Enter manually
- Use 0%

## 4. Select constraints

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

## 5. Run optimizations

The app can run:

- Equal Weight
- Max Return
- Min Volatility
- Max Sharpe
- Target Return
- Target Risk
- Efficient Frontier

## 6. Export results

After optimization, open the `Export` tab and download the polished Excel report. It includes a dashboard, summary tables, weights, group weights, asset summary, efficient frontier data, covariance, correlation, constraint settings and validation messages.
