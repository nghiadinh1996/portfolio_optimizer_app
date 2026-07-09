# Portfolio Optimizer App

A reusable Streamlit dashboard that automates the portfolio optimization workflow from the original Excel model.

## Version

Version 1.0 combines the next-stage polish work into one release:

- Better report export
- Cleaner dashboard charts
- Save/load constraint presets
- Easier local launch scripts
- User documentation
- Deployment guide

## What the app does

- Reads `data.xlsx`
- Calculates monthly returns from price/index levels
- Calculates demeaned returns
- Builds the monthly population covariance matrix and correlation matrix
- Supports manual expected returns or historical returns
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

The app expects a workbook named `data.xlsx` in the same folder as `app.py`.

Required sheets:

1. `prices`
   - `Date` column
   - One price/index-level column per asset

2. `asset_info`
   - `Asset`
   - `Asset Class`
   - `Region`
   - `Subgroup`

3. `expected_returns`
   - `Asset`
   - `Expected Annual Return`

4. `classification_guide`
   - Optional reference sheet explaining how to classify assets

Asset names must match exactly across `prices`, `asset_info`, and `expected_returns`.

Expected returns should be entered as Excel percentages, such as `8.97%`, or decimals, such as `0.0897`. Do not enter `8.97`, because that means 897% to Python.

## Asset classification guide

Use the `classification_guide` sheet when changing to a new asset universe.

| Column | What it means | Built-in constraint trigger |
|---|---|---|
| `Asset` | Asset name. Must match `prices` and `expected_returns`. | Exact asset match |
| `Asset Class` | Broad bucket such as Equity, Fixed Income, Cash, Alternative, Commodity, Real Estate, Currency, Other. | Equity / Fixed Income / Cash constraints |
| `Region` | Geographic exposure such as Domestic, Foreign, Global, Developed Ex-US, Emerging Market. | Foreign equity constraint uses `Region = Foreign` |
| `Subgroup` | More specific bucket such as US Equity, Developed, Emerging, Bond, Cash, REIT, Gold, Sector. | Developed / Emerging constraints |

For built-in constraints to work, use these exact labels when relevant: `Equity`, `Fixed Income`, `Cash`, `Foreign`, `Developed`, and `Emerging`.

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
