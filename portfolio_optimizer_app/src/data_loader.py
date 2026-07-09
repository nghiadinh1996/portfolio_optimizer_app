from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd

REQUIRED_SHEETS = {"prices", "asset_info", "expected_returns"}
REQUIRED_ASSET_INFO_COLUMNS = {"Asset", "Asset Class", "Region", "Subgroup"}
REQUIRED_EXPECTED_RETURN_COLUMNS = {"Asset", "Expected Annual Return"}


@dataclass(frozen=True)
class PortfolioInputData:
    """Clean input data loaded from the standardized workbook."""

    prices: pd.DataFrame
    asset_info: pd.DataFrame
    expected_returns: pd.Series

    @property
    def assets(self) -> list[str]:
        return [c for c in self.prices.columns if c != "Date"]


def _normalize_asset_names(values: Iterable[object]) -> list[str]:
    return [str(v).strip() for v in values]


def load_portfolio_workbook(path: str | Path) -> PortfolioInputData:
    """Load and validate the standardized portfolio optimizer workbook.

    Expected workbook structure:
      - prices: Date column + one column per asset with price/index levels
      - asset_info: Asset, Asset Class, Region, Subgroup
      - expected_returns: Asset, Expected Annual Return
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    xl = pd.ExcelFile(path)
    missing_sheets = REQUIRED_SHEETS - set(xl.sheet_names)
    if missing_sheets:
        raise ValueError(f"Missing required sheet(s): {sorted(missing_sheets)}")

    prices = pd.read_excel(path, sheet_name="prices")
    asset_info = pd.read_excel(path, sheet_name="asset_info")
    expected = pd.read_excel(path, sheet_name="expected_returns")

    if "Date" not in prices.columns:
        raise ValueError("The prices sheet must contain a 'Date' column.")

    missing_asset_info_cols = REQUIRED_ASSET_INFO_COLUMNS - set(asset_info.columns)
    if missing_asset_info_cols:
        raise ValueError(
            f"asset_info is missing required column(s): {sorted(missing_asset_info_cols)}"
        )

    missing_expected_cols = REQUIRED_EXPECTED_RETURN_COLUMNS - set(expected.columns)
    if missing_expected_cols:
        raise ValueError(
            f"expected_returns is missing required column(s): {sorted(missing_expected_cols)}"
        )

    prices = prices.copy()
    prices["Date"] = pd.to_datetime(prices["Date"], errors="coerce")
    if prices["Date"].isna().any():
        raise ValueError("The prices sheet contains invalid or missing dates.")

    prices = prices.sort_values("Date").reset_index(drop=True)
    if prices["Date"].duplicated().any():
        duplicated = prices.loc[prices["Date"].duplicated(), "Date"].dt.strftime("%Y-%m-%d").tolist()
        raise ValueError(f"The prices sheet contains duplicated dates: {duplicated[:5]}")

    assets = [str(c).strip() for c in prices.columns if c != "Date"]
    if not assets:
        raise ValueError("The prices sheet must contain at least one asset column.")

    prices = prices.rename(columns={c: str(c).strip() for c in prices.columns})
    for asset in assets:
        prices[asset] = pd.to_numeric(prices[asset], errors="coerce")

    if prices[assets].isna().any().any():
        bad_assets = prices[assets].columns[prices[assets].isna().any()].tolist()
        raise ValueError(f"The prices sheet has missing or non-numeric price data in: {bad_assets}")

    if (prices[assets] <= 0).any().any():
        bad_assets = prices[assets].columns[(prices[assets] <= 0).any()].tolist()
        raise ValueError(f"Price/index levels must be positive. Problem asset(s): {bad_assets}")

    asset_info = asset_info.copy()
    asset_info["Asset"] = _normalize_asset_names(asset_info["Asset"])
    asset_info = asset_info.drop_duplicates(subset=["Asset"], keep="first")

    expected = expected.copy()
    expected["Asset"] = _normalize_asset_names(expected["Asset"])
    expected["Expected Annual Return"] = pd.to_numeric(
        expected["Expected Annual Return"], errors="coerce"
    )

    asset_set = set(assets)
    info_set = set(asset_info["Asset"])
    expected_set = set(expected["Asset"])

    missing_info = asset_set - info_set
    missing_expected = asset_set - expected_set
    extra_info = info_set - asset_set
    extra_expected = expected_set - asset_set

    if missing_info:
        raise ValueError(f"asset_info is missing asset(s): {sorted(missing_info)}")
    if missing_expected:
        raise ValueError(f"expected_returns is missing asset(s): {sorted(missing_expected)}")
    if extra_info:
        raise ValueError(f"asset_info contains asset(s) not in prices: {sorted(extra_info)}")
    if extra_expected:
        raise ValueError(f"expected_returns contains asset(s) not in prices: {sorted(extra_expected)}")
    if expected["Expected Annual Return"].isna().any():
        bad_assets = expected.loc[expected["Expected Annual Return"].isna(), "Asset"].tolist()
        raise ValueError(f"Expected returns are missing or non-numeric for: {bad_assets}")

    # Align metadata and expected return series to the exact order of price columns.
    asset_info = asset_info.set_index("Asset").loc[assets].reset_index()
    expected_returns = expected.set_index("Asset").loc[assets, "Expected Annual Return"]
    expected_returns.name = "Expected Annual Return"

    return PortfolioInputData(
        prices=prices[["Date", *assets]],
        asset_info=asset_info,
        expected_returns=expected_returns,
    )
