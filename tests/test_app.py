from streamlit.testing.v1 import AppTest

from src.settings import ROOT


def test_app_loads_and_widgets_filter_without_exceptions():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    assert not app.exception
    assert len(app.button) == 18
    assert len(app.get("plotly_chart")) == 2
    app.radio(key="geo_mode").set_value("Select countries").run()
    assert not app.exception
    app.multiselect(key="geo_countries").set_value(["China", "France"]).run()
    assert not app.exception
    app.button(key="geo_type_Biology").click().run()
    assert not app.exception
    assert app.session_state["geo_domain"] == "Biology"
    app.selectbox(key="geo_period").set_value(0).run()
    assert not app.exception
    app.button(key="geo_type_Materials science").click().run()
    assert not app.exception
    assert any("No models with known origins" in info.value for info in app.info)
    app.radio(key="geo_mode").set_value("All countries").run()
    app.selectbox(key="geo_period").set_value(2).run()
    app.button(key="geo_type_Language").click().run()
    app.checkbox(key="geo_expanded").check().run()
    assert not app.exception
    assert app.session_state["geo_expanded"] is True


def test_empty_country_selection_is_handled():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    app.radio(key="geo_mode").set_value("Select countries").run()
    app.multiselect(key="geo_countries").set_value([]).run()
    assert not app.exception
    assert any("Choose at least one country" in info.value for info in app.info)


def test_accessibility_metrics_follow_period():
    from src.data import accessibility_by_country, in_period, load_models
    models = load_models(ROOT / "data/processed/models_clean.csv")
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    for period_index, period in [(2, (2021, 2025)), (0, (2011, 2015))]:
        app.selectbox(key="geo_period").set_value(period_index).run()
        assert not app.exception
        table = accessibility_by_country(in_period(models, *period))
        metric = next(m for m in app.metric if m.label == "Countries with open-weight models")
        assert metric.value == f'{int(table["Open weights"].gt(0).sum())} / {len(table)}'
