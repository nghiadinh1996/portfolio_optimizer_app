from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Any

import pandas as pd

REQUIRED_SHEETS = {"prices", "asset_info"}
REQUIRED_ASSET_INFO_COLUMNS = {"Asset", "Asset Class", "Region", "Subgroup"}
REQUIRED_EXPECTED_RETURN_COLUMNS = {"Asset", "Expected Annual Return"}


@dataclass(frozen=True)
class PortfolioInputData:
    """Clean input data loaded from the standardized workbook."""

    prices: pd.DataFrame
    asset_info: pd.DataFrame
    expected_returns: pd.Series
    expected_returns_available: bool = False
    validation_warnings: list[str] = field(default_factory=list)

    @property
    def assets(self) -> list[str]:
        return [c for c in self.prices.columns if c != "Date"]


def _normalize_asset_names(values: Iterable[object]) -> list[str]:
    return [str(v).strip() for v in values]


def _format_list(values: Iterable[object], max_items: int = 8) -> str:
    values = [str(v) for v in values]
    if len(values) <= max_items:
        return ", ".join(values)
    return ", ".join(values[:max_items]) + f", ... and {len(values) - max_items} more"


def _drop_blank_asset_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Drop fully blank rows and blank Asset rows from optional template ranges.

    The Excel template may contain formulas down the Asset column so names can
    auto-populate from prices. Blank formula rows and placeholder values such as 0 should not be treated as
    extra missing assets.
    """
    if df.empty or "Asset" not in df.columns:
        return df
    cleaned = df.dropna(how="all").copy()
    asset_text = cleaned["Asset"].astype(str).str.strip()
    asset_text_lower = asset_text.str.lower()
    placeholder_mask = (
        cleaned["Asset"].isna()
        | asset_text.eq("")
        | asset_text_lower.isin({"nan", "none", "null"})
        | asset_text.isin({"0", "0.0"})
    )
    cleaned = cleaned[~placeholder_mask]
    return cleaned.reset_index(drop=True)


def _formula_like_assets(df: pd.DataFrame) -> list[str]:
    if df.empty or "Asset" not in df.columns:
        return []
    return df.loc[df["Asset"].astype(str).str.strip().str.startswith("="), "Asset"].astype(str).tolist()


def _fill_template_asset_names_by_position(df: pd.DataFrame, assets: list[str]) -> pd.DataFrame:
    """Fill blank/formula Asset cells by row order from prices headers.

    This lets the app read a freshly generated template even if Excel has not
    saved cached values for the auto-populated Asset formulas. The user still
    controls the classification columns.
    """
    if df.empty or "Asset" not in df.columns:
        return df
    filled = df.copy().reset_index(drop=True)
    filled["Asset"] = filled["Asset"].astype("object")
    for pos in range(len(filled)):
        asset_value = filled.at[pos, "Asset"]
        asset_text = "" if pd.isna(asset_value) else str(asset_value).strip()
        if (not asset_text or asset_text.lower() in {"nan", "none", "null"} or asset_text in {"0", "0.0"} or asset_text.startswith("=")) and pos < len(assets):
            filled.at[pos, "Asset"] = assets[pos]
    return filled


def _missing_value_locations(df: pd.DataFrame, columns: list[str], max_items: int = 8) -> list[str]:
    locations: list[str] = []
    for asset in columns:
        bad_rows = df.index[df[asset].isna()].tolist()
        for idx in bad_rows[:max_items]:
            date_value = df.loc[idx, "Date"] if "Date" in df.columns else idx
            if hasattr(date_value, "strftime"):
                date_value = date_value.strftime("%Y-%m-%d")
            locations.append(f"{asset} on {date_value}")
            if len(locations) >= max_items:
                return locations
    return locations


def _validate_expected_return_scale(expected: pd.DataFrame) -> None:
    """Catch the common error of typing 8.97 instead of 8.97% / 0.0897."""
    suspicious = expected[expected["Expected Annual Return"].abs() > 1.0]
    if not suspicious.empty:
        examples = [
            f"{row['Asset']}={row['Expected Annual Return']}"
            for _, row in suspicious.iterrows()
        ]
        raise ValueError(
            "Expected Annual Return values must be stored as decimals. "
            "For example, 8.97% should appear in Excel as 8.97% or 0.0897, not 8.97. "
            f"Suspicious value(s): {_format_list(examples)}"
        )


def load_portfolio_workbook(source: str | Path | Any) -> PortfolioInputData:
    """Load and validate the standardized portfolio optimizer workbook.

    The source can be either a local file path, such as ``data.xlsx``, or a
    Streamlit uploaded file object from ``st.file_uploader``.

    Expected workbook structure:
      - prices: Date column + one column per asset with price/index levels
      - asset_info: Asset, Asset Class, Region, Subgroup
      - expected_returns: Asset, Expected Annual Return (optional)
    """
    workbook_name = getattr(source, "name", None) or str(source)
    if isinstance(source, (str, Path)):
        source = Path(source)
        workbook_name = source.name
        if not source.exists():
            raise FileNotFoundError(
                f"Input file not found: {source}. Upload a completed workbook or include data.xlsx in the app folder."
            )

    try:
        if hasattr(source, "seek"):
            source.seek(0)
        xl = pd.ExcelFile(source)
    except Exception as exc:
        raise ValueError(f"Could not open workbook '{workbook_name}'. Make sure it is a valid .xlsx file. Detail: {exc}") from exc

    missing_sheets = REQUIRED_SHEETS - set(xl.sheet_names)
    if missing_sheets:
        raise ValueError(
            f"Missing required sheet(s): {sorted(missing_sheets)}. "
            "The workbook must include prices and asset_info. expected_returns is optional."
        )

    prices = xl.parse(sheet_name="prices")
    asset_info = xl.parse(sheet_name="asset_info")
    expected = xl.parse(sheet_name="expected_returns") if "expected_returns" in xl.sheet_names else pd.DataFrame()

    prices = prices.rename(columns={c: str(c).strip() for c in prices.columns})
    asset_info = asset_info.rename(columns={c: str(c).strip() for c in asset_info.columns})
    expected = expected.rename(columns={c: str(c).strip() for c in expected.columns}) if not expected.empty else expected
    asset_info = asset_info.dropna(how="all").reset_index(drop=True)
    expected = expected.dropna(how="all").reset_index(drop=True) if not expected.empty else expected

    warnings: list[str] = []

    if "Date" not in prices.columns:
        raise ValueError("The prices sheet must contain a 'Date' column.")

    missing_asset_info_cols = REQUIRED_ASSET_INFO_COLUMNS - set(asset_info.columns)
    if missing_asset_info_cols:
        raise ValueError(
            f"asset_info is missing required column(s): {sorted(missing_asset_info_cols)}"
        )

    expected_returns_available = False
    expected_missing_reason = "expected_returns sheet was not found" if expected.empty else ""
    if not expected.empty:
        missing_expected_cols = REQUIRED_EXPECTED_RETURN_COLUMNS - set(expected.columns)
        if missing_expected_cols:
            warnings.append(
                f"expected_returns was ignored because it is missing column(s): {sorted(missing_expected_cols)}. Historical returns will be used instead if manual expected returns are selected."
            )
            expected = pd.DataFrame()
            expected_missing_reason = "expected_returns sheet has missing required columns"

    prices = prices.copy()

    duplicate_columns = prices.columns[prices.columns.duplicated()].tolist()
    if duplicate_columns:
        raise ValueError(f"The prices sheet has duplicate column name(s): {_format_list(duplicate_columns)}")

    prices["Date"] = pd.to_datetime(prices["Date"], errors="coerce")
    if prices["Date"].isna().any():
        bad_rows = (prices.index[prices["Date"].isna()] + 2).tolist()
        raise ValueError(f"The prices sheet contains invalid or missing dates in Excel row(s): {_format_list(bad_rows)}")

    prices = prices.sort_values("Date").reset_index(drop=True)
    if prices["Date"].duplicated().any():
        duplicated = prices.loc[prices["Date"].duplicated(), "Date"].dt.strftime("%Y-%m-%d").tolist()
        raise ValueError(f"The prices sheet contains duplicated dates: {_format_list(duplicated)}")

    assets = [str(c).strip() for c in prices.columns if c != "Date"]
    if not assets:
        raise ValueError("The prices sheet must contain at least one asset column.")

    blank_assets = [asset for asset in assets if not asset or asset.lower() == "nan"]
    if blank_assets:
        raise ValueError("The prices sheet contains blank asset column names. Rename every asset column.")

    if len(prices) < 2:
        raise ValueError("The prices sheet must contain at least two price rows to calculate returns.")

    for asset in assets:
        prices[asset] = pd.to_numeric(prices[asset], errors="coerce")

    if prices[assets].isna().any().any():
        bad_assets = prices[assets].columns[prices[assets].isna().any()].tolist()
        locations = _missing_value_locations(prices, bad_assets)
        raise ValueError(
            "The prices sheet has missing or non-numeric price data. "
            f"Problem asset(s): {_format_list(bad_assets)}. "
            f"Example location(s): {_format_list(locations)}"
        )

    if (prices[assets] <= 0).any().any():
        bad_assets = prices[assets].columns[(prices[assets] <= 0).any()].tolist()
        raise ValueError(f"Price/index levels must be positive. Problem asset(s): {_format_list(bad_assets)}")

    # Monthly spacing is not mandatory, but warn because the app annualizes using monthly assumptions.
    date_diffs = prices["Date"].diff().dt.days.dropna()
    if not date_diffs.empty and ((date_diffs < 25) | (date_diffs > 35)).any():
        warnings.append(
            "The date spacing is not consistently monthly. The app will still run, but return and volatility annualization assumes monthly observations."
        )

    asset_info = _fill_template_asset_names_by_position(asset_info, assets)
    asset_info = _drop_blank_asset_rows(asset_info)
    expected = _fill_template_asset_names_by_position(expected, assets)
    expected = _drop_blank_asset_rows(expected)

    asset_info = asset_info.copy()
    asset_info["Asset"] = _normalize_asset_names(asset_info["Asset"])
    if asset_info["Asset"].duplicated().any():
        duplicated_info = asset_info.loc[asset_info["Asset"].duplicated(), "Asset"].tolist()
        warnings.append(
            f"asset_info has duplicate asset row(s). The first row was kept for: {_format_list(duplicated_info)}"
        )
    asset_info = asset_info.drop_duplicates(subset=["Asset"], keep="first")

    for col in REQUIRED_ASSET_INFO_COLUMNS:
        if asset_info[col].isna().any() or asset_info[col].astype(str).str.strip().eq("").any():
            bad = asset_info.loc[asset_info[col].isna() | asset_info[col].astype(str).str.strip().eq(""), "Asset"].tolist()
            raise ValueError(f"asset_info column '{col}' has missing value(s) for: {_format_list(bad)}")
        asset_info[col] = asset_info[col].astype(str).str.strip()

    asset_set = set(assets)
    info_set = set(asset_info["Asset"])

    missing_info = asset_set - info_set
    extra_info = info_set - asset_set

    if missing_info:
        raise ValueError(f"asset_info is missing asset(s): {_format_list(sorted(missing_info))}")
    if extra_info:
        raise ValueError(f"asset_info contains asset(s) not in prices: {_format_list(sorted(extra_info))}")

    # expected_returns is optional. If it is missing, incomplete, mismatched, or blank,
    # the app will fall back to historical returns instead of blocking the workbook.
    if expected.empty:
        expected_returns = pd.Series(index=assets, dtype=float, name="Expected Annual Return")
        if expected_missing_reason:
            warnings.append(
                f"Manual expected returns are unavailable because {expected_missing_reason}. Historical returns will be used instead if needed."
            )
    else:
        expected = expected.copy()
        expected["Asset"] = _normalize_asset_names(expected["Asset"])
        if expected["Asset"].duplicated().any():
            duplicated_expected = expected.loc[expected["Asset"].duplicated(), "Asset"].tolist()
            warnings.append(
                f"expected_returns has duplicate asset row(s). The first row was kept for: {_format_list(duplicated_expected)}"
            )
        expected = expected.drop_duplicates(subset=["Asset"], keep="first")
        expected["Expected Annual Return"] = pd.to_numeric(
            expected["Expected Annual Return"], errors="coerce"
        )

        expected_set = set(expected["Asset"])
        missing_expected = asset_set - expected_set
        extra_expected = expected_set - asset_set
        missing_values = expected.loc[
            expected["Asset"].isin(asset_set) & expected["Expected Annual Return"].isna(), "Asset"
        ].tolist()
        suspicious = expected.loc[
            expected["Asset"].isin(asset_set) & expected["Expected Annual Return"].abs().gt(1.0), ["Asset", "Expected Annual Return"]
        ]

        if missing_expected or extra_expected or missing_values or not suspicious.empty:
            reasons = []
            if missing_expected:
                reasons.append(f"missing asset(s): {_format_list(sorted(missing_expected))}")
            if extra_expected:
                reasons.append(f"extra asset(s) not in prices: {_format_list(sorted(extra_expected))}")
            if missing_values:
                reasons.append(f"blank/non-numeric return(s): {_format_list(missing_values)}")
            if not suspicious.empty:
                examples = [f"{row['Asset']}={row['Expected Annual Return']}" for _, row in suspicious.iterrows()]
                reasons.append(
                    "return value(s) look like percentages entered as whole numbers, such as "
                    f"{_format_list(examples)}"
                )
            warnings.append(
                "Manual expected returns are unavailable because expected_returns is incomplete or mismatched ("
                + "; ".join(reasons)
                + "). Historical returns will be used instead if manual expected returns are selected."
            )
            expected_returns = pd.Series(index=assets, dtype=float, name="Expected Annual Return")
        else:
            expected_returns = expected.set_index("Asset").loc[assets, "Expected Annual Return"]
            expected_returns.name = "Expected Annual Return"
            expected_returns_available = True

    asset_classes = set(asset_info["Asset Class"].str.lower())
    if "equity" not in asset_classes:
        warnings.append("No assets are classified as Asset Class = Equity. Equity constraints will be infeasible if activated.")
    if "fixed income" not in asset_classes:
        warnings.append("No assets are classified as Asset Class = Fixed Income. Fixed income constraints will be infeasible if activated.")
    if "cash" not in asset_classes:
        warnings.append("No assets are classified as Asset Class = Cash. Cash constraints will be infeasible if activated.")

    # Align metadata to the exact order of price columns.
    asset_info = asset_info.set_index("Asset").loc[assets].reset_index()

    return PortfolioInputData(
        prices=prices[["Date", *assets]],
        asset_info=asset_info,
        expected_returns=expected_returns,
        expected_returns_available=expected_returns_available,
        validation_warnings=warnings,
    )
