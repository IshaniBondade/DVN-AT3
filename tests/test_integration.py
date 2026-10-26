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
    for source, output in [("Country (of organization)", "country_raw"), ("Organization", "org_raw"), ("Model accessibility", "accessibility"), ("Open model weights?", "open_model_weights")]:
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
    app.slider[0].set_value((2021, 2025)).run()
    assert not app.exception
    app.checkbox[0].check().run()
    assert not app.exception
    shared = pd.read_csv(ROOT / "data/processed/models_clean.csv")
    filtered = shared[shared.year.between(2021, 2025) & shared.frontier]
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
    app.slider[0].set_value((2026, 2026)).run()
    assert not app.exception
    assert any("No models fall" in w.value for w in app.warning)
