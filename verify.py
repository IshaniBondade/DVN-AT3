from pathlib import Path

import pandas as pd


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

for start, end in [(2011, 2015), (2016, 2020), (2021, 2025)]:
    total = int(years.between(start, end).sum())
    print(f"{start}–{end}:  {total:,}")
    print()


# Count open-weight models only for 2021–2025.
selected = data.loc[years.between(2021, 2025)]

open_weights = (
    selected["Open model weights?"]
    .fillna("")
    .str.strip()
    .str.casefold()
    .eq("yes")
)

print("TOTAL OPEN-WEIGHT MODELS")
print()
print(f"2021–2025:  {int(open_weights.sum()):,}")
print()
