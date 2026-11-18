"""Adapter between the shared dashboard data and the Geography feature."""
import streamlit as st
from src.views import render as render_geography


def geography_models(df):
    """Keep one row per model and preserve every source country affiliation."""
    required = {"pub_date", "org_raw", "country_raw", "accessibility"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError("Rebuild shared data with python scripts/make_processed.py. Missing: " + ", ".join(sorted(missing)))
    return df.drop(columns=["country"], errors="ignore").rename(columns={
        "pub_date": "publication_date", "org_raw": "organization",
        "country_raw": "country", "accessibility": "model_accessibility",
    }).copy()


def render(df, df_all):
    st.header("Geography")
    st.markdown(
        "Explore where notable AI models are developed, compare country shares across five-year periods, "
        "and drill down into model details. "
        "*Year, sector and frontier filters apply.*"
    )
    try:
        models = geography_models(df)
    except ValueError as error:
        st.error(str(error))
        return
    render_geography(models, key_prefix="geo_", show_header=False)
