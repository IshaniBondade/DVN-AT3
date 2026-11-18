from pathlib import Path
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest
from tabs.geography import geography_models
from src.data import normalize_models, country_summary, accessibility_by_country

ROOT = Path(__file__).resolve().parents[1]


def test_shared_pipeline_preserves_source_fields():
    raw = pd.read_csv(ROOT / "data/raw/notable_ai_models.csv", keep_default_na=False)
    processed = pd.read_csv(ROOT / "data/processed/models_clean.csv", keep_default_na=False).sort_values("source_record")
    assert len(processed) == len(raw)
    assert processed["source_record"].tolist() == list(range(1, len(raw) + 1))
    for source, output in [("Country (of organization)", "country_raw"), ("Organization", "org_raw"), ("Model accessibility", "accessibility"), ("Open model weights?", "open_model_weights"), ("Task", "task"), ("Link", "link")]:
        assert raw[source].tolist() == processed[output].tolist()
    models = normalize_models(geography_models(processed))
    assert country_summary(models)["share"].sum() == pytest.approx(1)
    assert models["countries"].map(len).gt(1).any()
    assert accessibility_by_country(models)["Open weights"].sum() > 0


def test_full_dashboard_and_shared_filters():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    assert not app.exception
    assert [t.label for t in app.tabs] == ["Overview", "Organisations", "Compute", "Geography", "Data & methods"]
    assert any(m.label == "Countries with open-weight models" for m in app.metric)
    app.slider[0].set_value((2022, 2026)).run()
    assert not app.exception
    app.checkbox[0].check().run()
    assert not app.exception
    shared = pd.read_csv(ROOT / "data/processed/models_clean.csv")
    filtered = shared[shared.year.between(2022, 2026) & shared.frontier]
    table = accessibility_by_country(normalize_models(geography_models(filtered)))
    metric = next(m for m in app.metric if m.label == "Countries with open-weight models")
    assert metric.value == f'{int(table["Open weights"].gt(0).sum())} / {len(table)}'
    app.radio(key="geo_mode").set_value("Select countries").run()
    app.multiselect(key="geo_countries").set_value([]).run()
    assert not app.exception
    app.selectbox(key="geo_period").set_value(0).run()
    assert not app.exception
    app.multiselect[0].set_value([]).run()
    assert not app.exception
    assert any("No models match" in i.value for i in app.info)


def test_years_outside_geography_are_handled():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    app.slider[0].set_value((2011, 2011)).run()
    assert not app.exception
    assert any("No models fall" in w.value for w in app.warning)


def test_2026_records_are_included_in_the_latest_period():
    shared = pd.read_csv(ROOT / "data/processed/models_clean.csv")
    records = shared.loc[shared.year.eq(2026)]
    assert len(records) == 84
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    assert app.selectbox(key="geo_period").options == ["2012–2016", "2017–2021", "2022–2026"]
    app.slider[0].set_value((2026, 2026)).run()
    assert not app.exception
    assert not any("No models fall" in warning.value for warning in app.warning)
    metrics = {metric.label: metric.value for metric in app.metric}
    assert metrics["Total models"] == "84"
    assert metrics["With country data"] == "83"
    assert metrics["Without country data"] == "1"
    assert any("2026 is partial" in item.value for item in app.markdown)
    values = app.dataframe[0].value
    assert values["Model credits*"].astype(float).sum() == pytest.approx(83)
    models = normalize_models(geography_models(records))
    assert country_summary(models)["share"].sum() == pytest.approx(1)
    categories = next(frame.value for frame in app.dataframe if "Model accessibility" in frame.value.columns and "Model records" in frame.value.columns)
    assert categories["Model records"].sum() == 84


def test_period_count_boxes_follow_filters_not_country_selection():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()

    def counts():
        assert not app.exception
        values = {metric.label: metric.value for metric in app.metric}
        return tuple(int(values[label].replace(",", "")) for label in
                     ["Total models", "With country data", "Without country data"])

    assert counts() == (499, 498, 1)
    app.radio(key="geo_mode").set_value("Select countries").run()
    app.multiselect(key="geo_countries").set_value(["China"]).run()
    assert counts() == (499, 498, 1)
    app.selectbox(key="geo_period").set_value(0).run()
    assert counts() == (143, 142, 1)
    app.slider[0].set_value((2026, 2026)).run()
    assert counts() == (0, 0, 0)
    app.selectbox(key="geo_period").set_value(2).run()
    assert counts() == (84, 83, 1)
    app.multiselect[0].set_value(["Industry"]).run()
    app.checkbox[0].check().run()
    shared = pd.read_csv(ROOT / "data/processed/models_clean.csv")
    expected = shared.loc[shared.year.eq(2026) & shared.sector.eq("Industry") & shared.frontier]
    known = int(expected.country_raw.fillna("").str.strip().ne("").sum())
    assert counts() == (len(expected), known, len(expected) - known)
