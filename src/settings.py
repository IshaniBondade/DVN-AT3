"""Read the feature's own settings without depending on the working directory."""
from __future__ import annotations

from pathlib import Path
import tomllib

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_settings(path: Path | None = None) -> dict:
    with (path or ROOT / "config.toml").open("rb") as handle:
        config = tomllib.load(handle)
    periods = config["analysis"]["periods"]
    previous_end = None
    for start, end in periods:
        if start > end or (previous_end is not None and start <= previous_end):
            raise ValueError("Analysis periods must be ordered and non-overlapping.")
        previous_end = end
    if not 0 <= config["analysis"]["default_period"] < len(periods):
        raise ValueError("default_period is outside the configured periods.")
    return config


def load_dashboard() -> dict:
    return yaml.safe_load((ROOT / "dashboard.yml").read_text(encoding="utf-8"))


def data_path(config: dict, name: str) -> Path:
    path = Path(config["data"][name])
    return path if path.is_absolute() else ROOT / path
