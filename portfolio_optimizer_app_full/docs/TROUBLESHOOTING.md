# Troubleshooting

## Python is not recognized

Try:

```bash
py --version
```

If that works, use `py` instead of `python`.

If neither works, install Python from python.org and select `Add python.exe to PATH` during installation.

## Streamlit is not recognized

Run:

```bash
py -m pip install -r requirements.txt
py -m streamlit run app.py
```

## The app cannot load the workbook

If you are using the included sample data, check that:

- `data.xlsx` or `sample_data.xlsx` is in the same folder as `app.py`
- It has the required sheets: `prices`, `asset_info`

If you are uploading your own file, check that:

- The file is an `.xlsx` workbook
- It was not left open and locked by Excel during upload
- It has the required sheets: `prices`, `asset_info`
- Asset names match exactly between `prices` and `asset_info`. The `expected_returns` sheet is optional

## Expected returns are missing or too high

The `expected_returns` sheet is optional. If it is missing, blank, incomplete, or mismatched, the app will use historical returns automatically.

If you want to use manual expected returns, make sure every asset is listed and the names match `prices` exactly.

## Expected returns are too high

Enter 8.97% in Excel as either:

- `8.97%`, or
- `0.0897`

Do not enter `8.97`, because Python reads that as 897%.

## Optimizer says constraints are infeasible

Common causes:

- Individual asset max is too low to add up to 100%
- Group minimums add to more than 100%
- Target return is above the maximum feasible return
- Target volatility is below the minimum feasible volatility
- Asset classifications do not match the constraint labels

For built-in group constraints, use these exact labels when relevant:

- `Asset Class`: `Equity`, `Fixed Income`, `Cash`
- `Region`: `Foreign`
- `Subgroup`: `Developed`, `Emerging`


## asset_info shows blank or formula-like asset names

The template uses Excel formulas to populate asset names from the `prices` sheet. Open the workbook in Excel, allow formulas to calculate, save it, and upload again. If formulas still do not calculate, paste the asset names manually into `asset_info` column A.
