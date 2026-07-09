# Project Status

## Version 1.2 completed features

- Standardized `data.xlsx` input workbook
- Streamlit file upload mode for user-provided `.xlsx` workbooks
- Downloadable Excel template from the app sidebar
- Dynamic asset count and timeframe support
- Price/index level input with automatic monthly return calculation
- Demeaned return calculation
- Population covariance matrix to match the original Excel workbook logic
- Manual expected return or historical return assumption selection, with automatic historical fallback
- Standard Sharpe ratio using an annual risk-free rate
- Flexible optional constraints
- Equal Weight, Max Return, Min Volatility, Max Sharpe, Target Return and Target Risk portfolios
- Efficient Frontier generation
- Feasibility checks for constraints, target return and target risk
- Polished Streamlit layout with tabs
- Risk-return chart, weight chart, allocation chart, metric comparison and correlation heatmap
- Polished Excel report export with a Dashboard sheet
- Constraint preset loading and saving through `presets.json`
- Local launcher scripts for Windows and Mac/Linux
- Streamlit theme configuration
- User guide, troubleshooting guide and deployment guide

## Suggested future upgrades

- Add custom group constraints from the UI
- Add Monte Carlo random portfolio simulation
- Add rolling risk/return diagnostics
- Add transaction cost and turnover constraints
- Add Black-Litterman expected return support
- Add factor exposure constraints
