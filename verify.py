from pathlib import Path

import pandas as pd

from src.settings import load_settings


# Load the dataset.
source = Path(__file__).resolve().parent / "data/raw/notable_ai_models.csv"
data = pd.read_csv(source)


# Read publication years.
dates = pd.to_datetime(
    data["Publication date"],
    format="mixed",
    errors="coerce",
)
years = dates.dt.year


# Count model records in each five-year period.
print()
print("TOTAL MODEL RECORDS")
print()

periods = load_settings()["analysis"]["periods"]
for start, end in periods:
    total = int(years.between(start, end).sum())
    print(f"{start}–{end}:  {total:,}")
    print()


# Count open-weight models for the latest configured period.
start, end = periods[-1]
selected = data.loc[years.between(start, end)]

open_weights = (
    selected["Open model weights?"]
    .fillna("")
    .str.strip()
    .str.casefold()
    .eq("yes")
)

print("TOTAL OPEN-WEIGHT MODELS")
print()
print(f"{start}–{end}:  {int(open_weights.sum()):,}")
print()
