# Portfolio Optimizer App

A reusable Streamlit dashboard that automates the portfolio optimization workflow from the original Excel model.

## Version

Version 1.3 adds optional expected-return handling. If the `expected_returns` sheet is missing, blank, incomplete, or mismatched, the app automatically falls back to historical returns instead of blocking the run.

- Upload user workbook through the Streamlit sidebar
- Optional `expected_returns` sheet with automatic historical-return fallback
- Download Excel template directly from the app
- Better report export
- Cleaner dashboard charts
- Save/load constraint presets
- Easier local launch scripts
- User documentation
- Deployment guide

## What the app does

- Reads the included `data.xlsx` / `sample_data.xlsx` or a user-uploaded `.xlsx` workbook
- Calculates monthly returns from price/index levels
- Calculates demeaned returns
- Builds the monthly population covariance matrix and correlation matrix
- Supports manual expected returns or historical returns, with automatic fallback to historical returns
- Uses standard Sharpe ratio: `(portfolio return - risk-free rate) / portfolio volatility`
- Supports flexible optional constraints
- Runs:
  - Equal Weight
  - Max Return
  - Min Volatility
  - Max Sharpe
  - Target Return
  - Target Risk
  - Efficient Frontier
- Displays:
  - Data preview
  - Assumption and constraint summary
  - Feasible range
  - Portfolio summary
  - Portfolio weights
  - Group weights
  - Risk-return chart
  - Efficient frontier chart
  - Allocation charts
  - Correlation heatmap
- Exports a polished Excel report

## Required Excel structure

For local use, the app can read `data.xlsx` in the same folder as `app.py`. For shared Streamlit links, users can download the template, fill it in, and upload their own `.xlsx` file through the sidebar.

Required sheets:

1. `prices`
   - `Date` column
   - One price/index-level column per asset

2. `asset_info`
   - `Asset`
   - `Asset Class`
   - `Region`
   - `Subgroup`

Optional sheets:

3. `expected_returns`
   - `Asset`
   - `Expected Annual Return`

4. `classification_guide`
   - Reference sheet explaining how to classify assets

Asset names must match exactly between `prices` and `asset_info`. If you use `expected_returns`, asset names in that sheet should also match exactly.

If the `expected_returns` sheet is missing, blank, incomplete, or mismatched, the app will automatically use historical returns. If expected returns are provided, enter them as Excel percentages, such as `8.97%`, or decimals, such as `0.0897`. Do not enter `8.97`, because that means 897% to Python.

## Asset classification guide

Use the `classification_guide` sheet when changing to a new asset universe.

| Column | What it means | Built-in constraint trigger |
|---|---|---|
| `Asset` | Asset name. Must match `prices`. If using manual expected returns, it should also match `expected_returns`. | Exact asset match |
| `Asset Class` | Broad bucket such as Equity, Fixed Income, Cash, Alternative, Commodity, Real Estate, Currency, Other. | Equity / Fixed Income / Cash constraints |
| `Region` | Geographic exposure such as Domestic, Foreign, Global, Developed Ex-US, Emerging Market. | Foreign equity constraint uses `Region = Foreign` |
| `Subgroup` | More specific bucket such as US Equity, Developed, Emerging, Bond, Cash, REIT, Gold, Sector. | Developed / Emerging constraints |

For built-in constraints to work, use these exact labels when relevant: `Equity`, `Fixed Income`, `Cash`, `Foreign`, `Developed`, and `Emerging`.


## Sharing the Streamlit app with other users

When deployed, other users should not edit your project `data.xlsx` file. Instead, the app supports this workflow:

1. User opens the Streamlit link.
2. User clicks **Download Excel template** in the sidebar.
3. User fills in the `prices` and `asset_info` sheets. `expected_returns` is optional.
4. User selects **Upload my own Excel file**.
5. User uploads the completed workbook.
6. The app runs optimization for that uploaded data during the current session.
7. User downloads the polished Excel report.

Uploaded files are processed in memory by the app and are not intentionally saved to the project folder.

## How to run

Open Command Prompt in this folder, then run:

```bash
py -m pip install -r requirements.txt
py -m streamlit run app.py
```

If `py` does not work, use:

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

On Windows, you can also double-click:

```text
run_app.bat
```

On Mac/Linux:

```bash
./run_app.sh
```

## Command-line tests

Calculation check:

```bash
py run_calculation_check.py
```

Validation check:

```bash
py run_validation_check.py
```

Optimization check:

```bash
py run_optimization_check.py
```

Full check, including Excel report export:

```bash
py run_full_check.py
```

## Main files

- `app.py`: Streamlit dashboard
- `data.xlsx`: Current input workbook
- `sample_data.xlsx`: Backup sample input workbook
- `presets.json`: Saved constraint presets
- `run_app.bat`: Windows one-click launcher
- `run_app.sh`: Mac/Linux launcher
- `src/data_loader.py`: Excel loading and workbook validation
- `src/validation.py`: model and constraint validation
- `src/calculations.py`: returns, covariance, volatility, Sharpe ratio
- `src/constraints.py`: optional constraint builder
- `src/optimizer.py`: Max Return, Min Volatility, Max Sharpe, Target Return, Target Risk
- `src/frontier.py`: Efficient Frontier generation
- `src/charts.py`: Plotly charts
- `src/reporting.py`: polished Excel export
- `src/presets.py`: constraint preset loading and saving
- `docs/`: user guide, troubleshooting and deployment notes

## Docs

Start here:

- `docs/USER_GUIDE.md`
- `docs/TROUBLESHOOTING.md`
- `docs/DEPLOYMENT.md`
- `docs/PROJECT_STATUS.md`

## Version 1.3 template update

The app now includes `portfolio_optimizer_template.xlsx` as the download template. In that workbook:

- `asset_info!A2:A200` auto-populates asset names from the headers in `prices` row 1.
- `expected_returns!A2:A200` auto-populates the same asset names.
- Users still need to fill or review `Asset Class`, `Region`, and `Subgroup` manually. Excel cannot infer asset classifications automatically.
- `expected_returns` remains optional. If it is missing, blank, or mismatched, the app falls back to historical returns.
- After editing the price headers, save the workbook before uploading so the auto-filled names are stored.
