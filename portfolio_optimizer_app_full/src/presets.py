from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import json
from typing import Any

from src.constraints import ConstraintConfig


DEFAULT_PRESETS: dict[str, dict[str, Any]] = {
    "Project Defaults": {
        "no_short": True,
        "individual_min": None,
        "individual_max": None,
        "equity_min": 0.60,
        "equity_max": 0.80,
        "fixed_income_min": 0.20,
        "fixed_income_max": 0.40,
        "cash_min": None,
        "cash_max": 0.20,
        "developed_min": None,
        "developed_max": None,
        "emerging_min": None,
        "emerging_max": None,
        "foreign_equity_max_pct_of_equity": 0.50,
    },
    "Unconstrained Long Only": {
        "no_short": True,
        "individual_min": None,
        "individual_max": None,
        "equity_min": None,
        "equity_max": None,
        "fixed_income_min": None,
        "fixed_income_max": None,
        "cash_min": None,
        "cash_max": None,
        "developed_min": None,
        "developed_max": None,
        "emerging_min": None,
        "emerging_max": None,
        "foreign_equity_max_pct_of_equity": None,
    },
    "Conservative Balanced": {
        "no_short": True,
        "individual_min": None,
        "individual_max": 0.45,
        "equity_min": 0.35,
        "equity_max": 0.60,
        "fixed_income_min": 0.30,
        "fixed_income_max": 0.55,
        "cash_min": None,
        "cash_max": 0.20,
        "developed_min": None,
        "developed_max": None,
        "emerging_min": None,
        "emerging_max": 0.10,
        "foreign_equity_max_pct_of_equity": 0.50,
    },
    "Growth Balanced": {
        "no_short": True,
        "individual_min": None,
        "individual_max": 0.40,
        "equity_min": 0.70,
        "equity_max": 0.90,
        "fixed_income_min": 0.10,
        "fixed_income_max": 0.25,
        "cash_min": None,
        "cash_max": 0.10,
        "developed_min": None,
        "developed_max": None,
        "emerging_min": None,
        "emerging_max": 0.15,
        "foreign_equity_max_pct_of_equity": 0.60,
    },
}


CONFIG_FIELDS = set(DEFAULT_PRESETS["Project Defaults"].keys())


def normalize_config_dict(values: dict[str, Any]) -> dict[str, Any]:
    """Return only fields accepted by ConstraintConfig and normalize blanks."""
    cleaned: dict[str, Any] = {}
    for key in CONFIG_FIELDS:
        value = values.get(key)
        if value == "" or value == "None":
            value = None
        cleaned[key] = value
    return cleaned


def load_presets(path: str | Path) -> dict[str, dict[str, Any]]:
    """Load user presets and merge them over built-in defaults."""
    path = Path(path)
    presets = {name: dict(values) for name, values in DEFAULT_PRESETS.items()}
    if not path.exists():
        return presets
    try:
        with path.open("r", encoding="utf-8") as f:
            user_presets = json.load(f)
    except Exception:
        return presets
    if not isinstance(user_presets, dict):
        return presets
    for name, values in user_presets.items():
        if isinstance(name, str) and isinstance(values, dict):
            presets[name] = normalize_config_dict(values)
    return presets


def save_presets(path: str | Path, presets: dict[str, dict[str, Any]]) -> None:
    path = Path(path)
    serializable = {
        str(name): normalize_config_dict(values)
        for name, values in presets.items()
        if str(name).strip()
    }
    with path.open("w", encoding="utf-8") as f:
        json.dump(serializable, f, indent=2, sort_keys=True)


def config_from_preset(values: dict[str, Any]) -> ConstraintConfig:
    return ConstraintConfig(**normalize_config_dict(values))


def config_to_dict(config: ConstraintConfig) -> dict[str, Any]:
    return normalize_config_dict(asdict(config))
