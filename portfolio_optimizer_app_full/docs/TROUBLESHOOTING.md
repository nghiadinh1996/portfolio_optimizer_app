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

## The app cannot load `data.xlsx`

Check that:

- The file is named exactly `data.xlsx`
- It is in the same folder as `app.py`
- It has the required sheets: `prices`, `asset_info`, `expected_returns`

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
