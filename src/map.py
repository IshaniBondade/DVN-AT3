"""Self-contained, responsive D3 map. No map tiles, CDN or API key needed."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit.components.v1 as components

ASSETS = Path(__file__).resolve().parent / "assets"


def map_html(summary: pd.DataFrame, geometry: dict, codes: dict, selected: list[str] | None, period: str) -> str:
    payload = {
        "world": geometry,
        "summary": summary.to_dict("records"),
        "codes": codes,
        "selected": selected,
        "period": period,
    }
    # Prevent a source label from closing the JSON script element.
    encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False).replace("<", "\\u003c")
    template = (ASSETS / "map.html").read_text(encoding="utf-8")
    return template.replace("__D3_SOURCE__", (ASSETS / "d3.min.js").read_text(encoding="utf-8")).replace("__MAP_DATA__", encoded)


def render_map(summary: pd.DataFrame, geometry: dict, codes: dict, selected: list[str] | None, period: str) -> None:
    components.html(map_html(summary, geometry, codes, selected, period), height=375, scrolling=False)
