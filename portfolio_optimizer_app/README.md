# Portfolio Optimizer App

This project turns the Excel portfolio optimization workflow into a reusable Python/Streamlit app.

## Current version

Version 0.1 includes the calculation engine:

- Loads `data.xlsx`
- Validates required sheets and asset names
- Calculates monthly returns from price/index levels
- Calculates demeaned returns
- Calculates monthly population covariance matrix, matching the Excel workbook logic
- Calculates correlation matrix
- Supports manual expected returns or historical returns
- Calculates annual return, annual volatility and standard Sharpe ratio for the equal-weight base portfolio

Optimization routines will be added in the next step.

## Required input workbook

The app expects a file named `data.xlsx` in the same folder as `app.py`.

Required sheets:

1. `prices`
   - Date column
   - One asset price/index-level column per asset
2. `asset_info`
   - Asset
   - Asset Class
   - Region
   - Subgroup
3. `expected_returns`
   - Asset
   - Expected Annual Return

## Run the calculation check

```bash
python run_calculation_check.py
```

## Run the Streamlit app

```bash
streamlit run app.py
```
