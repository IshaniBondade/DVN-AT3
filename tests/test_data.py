from pathlib import Path

import pandas as pd
import pytest

from src.data import build_processed, country_summary, credits, distribution_rows, domain_counts, in_period, load_models, model_details, normalize_models, shares_over_time, validate_dataset, with_domain
from src.settings import ROOT, load_settings


def make_frame(rows):
    return normalize_models(pd.DataFrame(rows, columns=["Model", "Organization", "Publication date", "Country (of organization)", "Domain"]))


@pytest.fixture
def synthetic():
    return make_frame([
        ["Joint", "Lab A,Lab B", "2021-01-01", "United States of America,United States of America,China", "Language,Vision"],
        ["Chinese", "Lab C", "2025-12-31", "China", "Language"],
        ["British", "Lab D", "2025-01-01", "United Kingdom", "Biology"],
        ["Unknown", "Lab E", "2024-01-01", "", "Language"],
    ])


@pytest.fixture(scope="module")
def snapshot():
    return load_models(ROOT / "data/processed/models_clean.csv")


def test_fractional_credit_deduplicates_origins(synthetic):
    c = credits(synthetic)
    assert c.groupby("record_id")["credit"].sum().tolist() == [1, 1, 1]
    summary = country_summary(synthetic).set_index("country")
    assert summary.loc["China", "credit"] == 1.5
    assert summary.loc["United States", "credit"] == .5
    assert summary.loc["China", "share"] == .5
    assert summary["share"].sum() == pytest.approx(1)


def test_type_share_uses_type_global_denominator(synthetic):
    summary = country_summary(with_domain(synthetic, "Language")).set_index("country")
    assert summary.loc["China", "share"] == .75
    assert summary.loc["United States", "share"] == .25


def test_country_selection_keeps_global_shares(synthetic):
    summary = country_summary(synthetic)
    selected = distribution_rows(summary, selected=["China"]).set_index("country")
    assert selected.loc["China", "share"] == .5
    assert selected.loc["Other origins", "share"] == .5
    assert selected["share"].sum() == pytest.approx(1)


def test_unobserved_selected_country_has_zero_share(synthetic):
    selected = distribution_rows(country_summary(synthetic), selected=["France"]).set_index("country")
    assert selected.loc["France", "share"] == 0
    assert selected.loc["Other origins", "share"] == 1


def test_empty_country_selection_is_explicit_other(synthetic):
    shown = distribution_rows(country_summary(synthetic), selected=[])
    assert shown["country"].tolist() == ["Other origins"]
    assert shown["share"].tolist() == [1]


def test_period_boundaries_include_both_end_years(synthetic):
    assert len(in_period(synthetic, 2021, 2025)) == 4
    assert in_period(synthetic, 2025, 2025)["model"].tolist() == ["Chinese", "British"]


def test_joint_orgs_are_not_assigned_to_both_countries(synthetic):
    summary = country_summary(synthetic).set_index("country")
    assert summary.loc["China", "organisation_labels"] == 1
    assert summary.loc["China", "top_developers"] == "Lab C"
    assert summary.loc["United States", "organisation_labels"] == 0


def test_multinational_stays_in_denominator():
    frame = make_frame([["A", "Lab", "2020-01-01", "Multinational", "Language"], ["B", "Lab", "2020-02-01", "China", "Language"]])
    summary = country_summary(frame).set_index("country")
    assert summary.loc["China", "share"] == .5
    assert summary.loc["Multinational", "share"] == .5


def test_types_overlap_but_each_country_distribution_totals_one(synthetic):
    counts = domain_counts(synthetic, ["Language", "Vision", "Biology"])
    assert counts["records"].sum() > len(synthetic)
    for domain in counts["domain"]:
        assert country_summary(with_domain(synthetic, domain))["share"].sum() == pytest.approx(1)


def test_no_origin_or_no_type_returns_empty_summary(synthetic):
    assert country_summary(synthetic.loc[synthetic["model"].eq("Unknown")]).empty
    assert country_summary(with_domain(synthetic, "Nonexistent")).empty


def test_invalid_dates_are_counted_and_excluded():
    frame = make_frame([["A", "Lab", "invalid", "China", "Language"], ["B", "Lab", "2022-01-01", "China", "Language"]])
    assert frame["model"].tolist() == ["B"]
    assert frame.attrs["validation"]["invalid_dates_excluded"] == 1


def test_schema_errors_are_actionable():
    with pytest.raises(ValueError, match="Missing required columns"):
        normalize_models(pd.DataFrame({"Model": ["A"]}))


def test_custom_column_mapping():
    frame = pd.DataFrame({"name": ["A"], "lab": ["Lab"], "released": ["2022-01-01"], "origin": ["China"], "kind": ["Language"]})
    model = normalize_models(frame, {"model": "name", "organization": "lab", "publication_date": "released", "country": "origin", "domain": "kind"})
    assert model.iloc[0]["countries"] == ("China",)


def test_exact_duplicate_removed_conflicting_identity_rejected():
    row = ["A", "Lab", "2020-01-01", "China", "Language"]
    frame = make_frame([row, row])
    assert len(frame) == 1
    assert frame.attrs["validation"]["exact_duplicates_removed"] == 1
    with pytest.raises(ValueError, match="Duplicate model identities"):
        make_frame([row, ["A", "Lab", "2020-01-01", "China", "Vision"]])


def test_model_trace_reconciles_to_country_credit(synthetic):
    detail = model_details(synthetic, "China", "Language")
    assert detail["country_credit"].sum() == 1.5
    assert detail["model"].tolist() == ["Chinese", "Joint"]
    assert detail["record_id"].nunique() == 2


def test_snapshot_period_counts(snapshot):
    report = validate_dataset(snapshot, load_settings()["analysis"]["periods"])
    assert [r["records"] for r in report["periods"]] == [105, 259, 494]
    assert [r["known_origin_records"] for r in report["periods"]] == [104, 259, 494]
    assert [r["named_origins"] for r in report["periods"]] == [14, 26, 21]


def test_snapshot_verified_shares_and_domains(snapshot):
    recent = in_period(snapshot, 2021, 2025)
    overall = country_summary(recent).set_index("country")
    assert overall.loc["China", "share"] == pytest.approx(.22081646423751688)
    assert overall.loc["China", "associated_models"] == 122
    assert overall.loc["China", "organisation_labels"] == 35
    language = country_summary(with_domain(recent, "Language")).set_index("country")
    assert len(with_domain(recent, "Language")) == 328
    assert language.loc["China", "share"] == pytest.approx(.2705792682926829)
    assert language.loc["United States", "share"] == pytest.approx(.5691290650406504, abs=1e-6)
    all_domains = {tag for tags in in_period(snapshot, 2011, 2025)["domains"] for tag in tags}
    assert len(all_domains) == 18


def test_time_distributions_total_100_percent(snapshot):
    table = shares_over_time(snapshot, [[2011, 2015], [2016, 2020], [2021, 2025]], ["United States", "China", "United Kingdom"])
    assert table.groupby("period")["share"].sum().tolist() == pytest.approx([1, 1, 1])


def test_processed_roundtrip_preserves_model_ids(tmp_path, snapshot):
    target = tmp_path / "models.csv"
    build_processed(ROOT / "data/raw/notable_ai_models.csv", target)
    # The group pipeline sorts by publication date; compare source identities.
    reloaded = load_models(target).sort_values("source_record")
    snapshot = snapshot.sort_values("source_record")
    assert reloaded["record_id"].tolist() == snapshot["record_id"].tolist()
    assert reloaded["countries"].tolist() == snapshot["countries"].tolist()


def test_every_domain_reconciles_in_every_period(snapshot):
    for start, end in load_settings()["analysis"]["periods"]:
        period = in_period(snapshot, start, end)
        for domain in {tag for tags in period["domains"] for tag in tags}:
            data = with_domain(period, domain)
            summary = country_summary(data)
            known = data["countries"].map(len).gt(0).sum()
            assert summary["credit"].sum() == pytest.approx(known)
            assert summary["share"].sum() == pytest.approx(1 if known else 0)


def test_accessibility_flags_fallback_unknown_and_joint_origins():
    from src.data import accessibility_by_country

    raw = pd.DataFrame([
        ["A", "Lab", "2022-01-01", "China,USA,USA", "Language", "Open weights (non-commercial)", ""],
        ["B", "Lab", "2022-01-02", "China", "Language", "Open weights (unrestricted)", "No"],
        ["C", "Lab", "2022-01-03", "China", "Language", "", ""],
        ["D", "Lab", "2022-01-04", "Multinational", "Language", "API access", "Yes"],
        ["E", "Lab", "2022-01-05", "", "Language", "API access", ""],
    ], columns=["Model", "Organization", "Publication date", "Country", "Domain", "Model accessibility", "Open model weights?"])
    models = normalize_models(raw)
    assert models["open_weight_status"].tolist() == ["Open weights", "Not open weights", "Unknown", "Open weights", "Not open weights"]
    table = accessibility_by_country(models).set_index("country")
    assert set(table.index) == {"China", "United States"}
    assert table.loc["China", "Open weights"] == 1
    assert table.loc["China", "Open-weight share"] == pytest.approx(1 / 3)
    assert table.loc["United States", "Total models"] == 1
    assert accessibility_by_country(models.iloc[:0]).empty


def test_accessibility_survives_processed_roundtrip(tmp_path):
    target = tmp_path / "models.csv"
    build_processed(ROOT / "data/raw/notable_ai_models.csv", target)
    raw = load_models(ROOT / "data/raw/notable_ai_models.csv")
    processed = load_models(target)
    for field in ["model_accessibility", "open_model_weights", "open_weight_status"]:
        assert raw[field].tolist() == processed[field].tolist()
    assert processed["open_weight_status"].eq("Open weights").any()
