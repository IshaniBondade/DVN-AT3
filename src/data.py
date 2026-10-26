"""Pure data transformations. Shares always retain the global denominator."""
from __future__ import annotations

from collections import Counter
import hashlib
from pathlib import Path
import re

import pandas as pd

ALIASES = {
    "model": ("model", "model_name"),
    "organization": ("organization", "org_raw", "organisation", "organizations", "organisations"),
    "publication_date": ("publication_date", "pub_date", "release_date", "date"),
    "country": ("country_raw", "country", "country_of_organization", "country_of_organisation", "countries"),
    "domain": ("domain", "domains", "ai_type"),
    "task": ("task", "tasks"),
    "link": ("link", "url", "source_url"),
    "model_accessibility": ("model_accessibility", "accessibility"),
    "open_model_weights": ("open_model_weights", "open_model_weights_"),
}
REQUIRED = ("model", "organization", "publication_date", "country", "domain")
COUNTRY_ALIASES = {
    "United States of America": "United States",
    "USA": "United States",
    "US": "United States",
    "UK": "United Kingdom",
}
SUMMARY_COLUMNS = ["country", "credit", "share", "associated_models", "organisation_labels", "top_developers"]


def _column_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).lower()).strip("_")


def tokens(value: object) -> tuple[str, ...]:
    """Parse source comma/semicolon tags, deduplicating before attribution."""
    if isinstance(value, (list, tuple, set)):
        values = list(value)
    elif value is None or pd.isna(value):
        return ()
    else:
        values = re.split(r"[,;]", str(value))
    return tuple(dict.fromkeys(str(v).strip() for v in values if str(v).strip()))


def _open_weight_status(row: pd.Series) -> str:
    """Prefer the explicit weights flag; infer only from labelled access modes."""
    flag = row["open_model_weights"].casefold()
    access = row["model_accessibility"].casefold()
    if flag == "yes":
        return "Open weights"
    if flag == "no":
        return "Not open weights"
    if access.startswith("open weights"):
        return "Open weights"
    if access in {"api access", "hosted access (no api)", "limited access", "unreleased"}:
        return "Not open weights"
    return "Unknown"


def accessibility_by_country(models: pd.DataFrame) -> pd.DataFrame:
    """Count associated records once per country; exclude unspecified origins."""
    rows = models[["record_id", "countries", "open_weight_status"]].explode("countries")
    rows = rows.loc[rows["countries"].notna() & rows["countries"].ne("Multinational")]
    columns = ["Open weights", "Not open weights", "Unknown"]
    if rows.empty:
        return pd.DataFrame(columns=["country", *columns, "Total models", "Open-weight share"])
    table = rows.groupby(["countries", "open_weight_status"]).size().unstack(fill_value=0)
    table = table.reindex(columns=columns, fill_value=0)
    table["Total models"] = table.sum(axis=1)
    table["Open-weight share"] = table["Open weights"] / table["Total models"]
    return table.rename_axis("country").reset_index().sort_values(
        ["Open weights", "country"], ascending=[False, True]).reset_index(drop=True)


def normalize_models(frame: pd.DataFrame, column_map: dict | None = None) -> pd.DataFrame:
    """Accept Epoch headers or the documented canonical schema.

    Invalid dates are reported and excluded. Missing origins remain visible as
    source records but cannot enter a country-share denominator. Exact duplicate
    input rows are removed; versions with distinct identities are retained.
    """
    original_count = len(frame)
    raw = frame.drop_duplicates().copy()
    lookup = {_column_key(c): c for c in raw.columns}
    fields: dict[str, str] = {}
    for target, aliases in ALIASES.items():
        override = (column_map or {}).get(target)
        if override:
            if override not in raw.columns:
                raise ValueError(f"Mapped column {override!r} for {target!r} is missing.")
            fields[target] = override
        else:
            source = next((lookup[a] for a in aliases if a in lookup), None)
            if source is not None:
                fields[target] = source
    missing = set(REQUIRED) - fields.keys()
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(sorted(missing)) + ". Set [columns] in config.toml to match your dataset.")
    result = pd.DataFrame(index=raw.index)
    for target in ALIASES:
        result[target] = raw[fields[target]].fillna("").astype(str).str.strip() if target in fields else ""
    if result["model"].eq("").any():
        raise ValueError("Model names must not be empty.")
    dates = pd.to_datetime(result["publication_date"], errors="coerce", utc=True, format="mixed")
    invalid_dates = int(dates.isna().sum())
    result["publication_date"] = dates.dt.tz_convert(None)
    result["source_record"] = raw["source_record"] if "source_record" in raw else pd.Series(range(1, len(frame) + 1), index=frame.index).loc[raw.index]
    result = result.loc[dates.notna()].copy()
    if result.empty:
        raise ValueError("No model records have a valid publication date.")
    result["open_weight_status"] = result.apply(_open_weight_status, axis=1)
    result["year"] = result["publication_date"].dt.year
    result["countries"] = result["country"].map(lambda v: tuple(dict.fromkeys(COUNTRY_ALIASES.get(c, c) for c in tokens(v))))
    result["domains"] = result["domain"].map(tokens)
    result["organisations"] = result["organization"].map(tokens)
    identities = result[["model", "organization", "publication_date"]].astype(str).agg("\x1f".join, axis=1)
    result["record_id"] = identities.map(lambda s: hashlib.sha256(s.encode()).hexdigest()[:16])
    if result["record_id"].duplicated().any():
        raise ValueError("Duplicate model identities have conflicting fields; reconcile them before computing shares.")
    result = result.reset_index(drop=True)
    result.attrs["validation"] = {
        "input_records": original_count,
        "exact_duplicates_removed": original_count - len(raw),
        "invalid_dates_excluded": invalid_dates,
        "usable_records": len(result),
        "missing_country_records": int(result["countries"].map(len).eq(0).sum()),
        "missing_domain_records": int(result["domains"].map(len).eq(0).sum()),
    }
    return result


def load_models(path: Path, column_map: dict | None = None) -> pd.DataFrame:
    return normalize_models(pd.read_csv(path, keep_default_na=False), column_map)


def in_period(models: pd.DataFrame, start: int, end: int) -> pd.DataFrame:
    return models.loc[models["year"].between(start, end)].copy()


def with_domain(models: pd.DataFrame, domain: str) -> pd.DataFrame:
    return models.loc[models["domains"].map(lambda values: domain in values)].copy()


def credits(models: pd.DataFrame) -> pd.DataFrame:
    known = models.loc[models["countries"].map(len).gt(0)].copy()
    if known.empty:
        return pd.DataFrame(columns=["record_id", "country", "credit"])
    known["credit"] = 1.0 / known["countries"].map(len)
    return known[["record_id", "countries", "credit"]].explode("countries").rename(columns={"countries": "country"}).reset_index(drop=True)


def country_summary(models: pd.DataFrame) -> pd.DataFrame:
    contribution = credits(models)
    if contribution.empty:
        return pd.DataFrame(columns=SUMMARY_COLUMNS)
    denominator = contribution["record_id"].nunique()
    summary = contribution.groupby("country", as_index=False).agg(credit=("credit", "sum"), associated_models=("record_id", "nunique"))
    summary["share"] = summary["credit"] / denominator
    orgs: dict[str, Counter] = {}
    for row in models.itertuples():
        if len(row.countries) == 1:
            orgs.setdefault(row.countries[0], Counter()).update(row.organisations)
    summary["organisation_labels"] = summary["country"].map(lambda c: len(orgs.get(c, {})))
    summary["top_developers"] = summary["country"].map(lambda c: " · ".join(o for o, _ in sorted(orgs.get(c, {}).items(), key=lambda p: (-p[1], p[0]))[:2]) or "None recorded")
    return summary[SUMMARY_COLUMNS].sort_values(["share", "country"], ascending=[False, True]).reset_index(drop=True)


def domain_counts(models: pd.DataFrame, all_domains: list[str]) -> pd.DataFrame:
    counts = Counter(tag for values in models["domains"] for tag in values)
    return pd.DataFrame([{"domain": d, "records": counts.get(d, 0)} for d in all_domains])


def distribution_rows(summary: pd.DataFrame, selected: list[str] | None = None, limit: int | None = 5) -> pd.DataFrame:
    """Filter displayed origins only. Never recalculate the global denominator."""
    if summary.empty:
        return summary.copy()
    if selected is not None:
        shown = summary.set_index("country").reindex(selected).reset_index()
        for field in ["credit", "share", "associated_models", "organisation_labels"]:
            shown[field] = shown[field].fillna(0)
        shown["top_developers"] = shown["top_developers"].fillna("None recorded")
        shown = shown.sort_values(["share", "country"], ascending=[False, True])
    else:
        shown = summary.copy() if limit is None else summary.head(limit).copy()
    residual = max(0.0, 1.0 - float(shown["share"].sum()))
    if residual > 1e-12:
        shown = pd.DataFrame([*shown.to_dict("records"), {"country": "Other origins", "credit": max(0.0, float(summary["credit"].sum() - shown["credit"].sum())), "share": residual, "associated_models": None, "organisation_labels": None, "top_developers": ""}], columns=SUMMARY_COLUMNS)
    return shown.reset_index(drop=True)


def shares_over_time(models: pd.DataFrame, periods: list, selected: list[str]) -> pd.DataFrame:
    frames = []
    for index, (start, end) in enumerate(periods):
        subset = in_period(models, start, end)
        table = distribution_rows(country_summary(subset), selected=selected)
        table["period"] = f"{start}–{end}"
        table["period_index"] = index
        table["known_models"] = int(subset["countries"].map(len).gt(0).sum())
        frames.append(table)
    return pd.concat(frames, ignore_index=True)


def model_details(models: pd.DataFrame, country: str, domain: str) -> pd.DataFrame:
    subset = with_domain(models, domain)
    subset = subset.loc[subset["countries"].map(lambda values: country in values)].copy()
    subset["country_credit"] = subset["countries"].map(lambda values: 1.0 / len(values))
    subset["publication_date"] = subset["publication_date"].dt.strftime("%Y-%m-%d")
    # Only web URLs are exposed as clickable links in the UI.
    subset["link"] = subset["link"].where(subset["link"].str.match(r"^https?://"), "")
    return subset.sort_values(["publication_date", "model"], ascending=[False, True])[["model", "organization", "publication_date", "country", "domain", "task", "model_accessibility", "open_weight_status", "country_credit", "link", "record_id", "source_record"]]


def build_processed(raw_path: Path, output_path: Path, column_map: dict | None = None) -> dict:
    frame = load_models(raw_path, column_map)
    export = frame[["record_id", "source_record", *ALIASES]].copy()
    export["publication_date"] = frame["publication_date"].dt.strftime("%Y-%m-%d")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    export.to_csv(output_path, index=False)
    return frame.attrs["validation"]


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_dataset(models: pd.DataFrame, periods: list) -> dict:
    report = {"validation": models.attrs.get("validation", {}), "periods": []}
    for start, end in periods:
        subset = in_period(models, start, end)
        summary = country_summary(subset)
        known = int(subset["countries"].map(len).gt(0).sum())
        total_credit = float(summary["credit"].sum())
        if abs(total_credit - known) > 1e-8:
            raise ValueError(f"Country credits do not reconcile for {start}–{end}.")
        if known and abs(float(summary["share"].sum()) - 1) > 1e-10:
            raise ValueError(f"Country shares do not total 100% for {start}–{end}.")
        report["periods"].append({"period": [start, end], "records": len(subset), "known_origin_records": known, "excluded_missing_origin": len(subset) - known, "named_origins": int(summary["country"].ne("Multinational").sum()), "credit_sum": total_credit, "share_sum": float(summary["share"].sum())})
    return report
