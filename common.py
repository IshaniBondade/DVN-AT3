"""Shared constants and helpers. Everyone imports from here; edit with care."""
from pathlib import Path
import pandas as pd
import streamlit as st

DATA_PATH = Path("data/processed/models_clean.csv")
DATA_DOWNLOADED = "19 Oct 2026"          # EDIT: the day you downloaded the raw file
DATA_LATEST_OBS = "30 Sep 2026"          # latest publication date in the data
SOURCE_LINE = (
    "Source: Epoch AI, 'Data on AI models'. Published online at epoch.ai. "
    "Retrieved from https://epoch.ai/data/ai-models. Licence: CC-BY 4.0. "
    f"Raw file downloaded {DATA_DOWNLOADED}; latest model in data: {DATA_LATEST_OBS}."
)

# Okabe-Ito colour-blind-safe palette
OKABE_ITO = ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9", "#F0E442", "#000000"]

@st.cache_data
def load_data() -> pd.DataFrame:
    return pd.read_csv(DATA_PATH, parse_dates=["pub_date"])