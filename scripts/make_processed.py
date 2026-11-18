"""Rebuild data/processed/models_clean.csv from data/raw/notable_ai_models.csv.

Run from the repo root:  python scripts/make_processed.py
One row per notable model. Nothing is dropped; missing values stay missing.
"""
from pathlib import Path
import pandas as pd

RAW = Path("data/raw/notable_ai_models.csv")
OUT = Path("data/processed/models_clean.csv")

# Judgement call, disclose it in the data dictionary: these names are merged
# into one parent so each parent's share is not understated.
ALIASES = {
    "DeepMind": "Google", "Google DeepMind": "Google", "Google Research": "Google",
    "Google Brain": "Google", "Google Cloud": "Google",
    "Meta AI": "Meta", "Facebook": "Meta", "Facebook AI Research": "Meta",
    "Facebook AI": "Meta",
    "Microsoft Research": "Microsoft", "Microsoft Research Asia": "Microsoft",
}

def first_listed(s):
    """Cells like 'Google,Stanford University' list several values; take the first."""
    if pd.isna(s):
        return None
    return s.split(",")[0].strip()

def sector(s):
    if pd.isna(s):
        return "Unknown"
    parts = {p.strip() for p in s.split(",")}
    if parts == {"Industry"}:
        return "Industry"
    if parts == {"Academia"}:
        return "Academia"
    if {"Industry", "Academia"} <= parts:
        return "Industry + Academia"
    return "Other"

raw = pd.read_csv(RAW)
df = pd.DataFrame({
    "model": raw["Model"],
    "pub_date": pd.to_datetime(raw["Publication date"], errors="coerce"),
    "org_raw": raw["Organization"],
    "domain": raw["Domain"],
    "parameters": raw["Parameters"],
    "compute_flop": raw["Training compute (FLOP)"],
    "frontier": raw["Frontier model"].eq(True),
    "accessibility": raw["Model accessibility"],
})
df["year"] = df["pub_date"].dt.year
df["org"] = raw["Organization"].map(first_listed).replace(ALIASES).fillna("Unknown")
df["n_orgs"] = raw["Organization"].fillna("").map(lambda s: len([p for p in s.split(",") if p.strip()]))
df["sector"] = raw["Organization categorization"].map(sector)
df["country"] = raw["Country (of organization)"].map(first_listed).fillna("Unknown")
df["compute_reported"] = df["compute_flop"].notna()
# the latest year in the data is partial, flag it so charts can label or exclude it
df["partial_year"] = df["year"] == df["pub_date"].max().year

# checks that could fail
assert len(df) == len(raw), "row count changed"
assert df["model"].is_unique, "model is not a unique key"
assert df["pub_date"].notna().all(), "unparseable dates"
assert int(df["frontier"].sum()) == int(raw["Frontier model"].eq(True).sum())

OUT.parent.mkdir(parents=True, exist_ok=True)
df.sort_values("pub_date", kind="stable").to_csv(OUT, index=False)
print(f"wrote {OUT}: {len(df)} rows, {df['compute_reported'].sum()} with compute, "
      f"{df['frontier'].sum()} frontier, dates {df['pub_date'].min().date()} to {df['pub_date'].max().date()}")