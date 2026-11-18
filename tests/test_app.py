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
    app.radio(key="geo_mode").set_value("Leading countries").run()
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


def test_selected_countries_without_period_records_remain_visible():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    app.radio(key="geo_mode").set_value("Select countries").run()
    selected = ["United States", "China", "Australia", "Czechia"]
    app.multiselect(key="geo_countries").set_value(selected).run()
    assert not app.exception
    values = app.table[0].value
    assert values.index.tolist() == selected
    assert values.loc["Czechia", "Global share"] == "0.00%"
    assert values.loc["Czechia", "Model credits*"] == "0.00"
    assert values.loc["Czechia", "Associated models"] == 0
    all_values = app.dataframe[0].value.set_index("Country / region")
    assert set(selected) < set(all_values.index)
    assert "France" in all_values.index
    assert all_values.loc["Czechia", "Associated models"] == 0
    assert all_values.loc["United States", "Global share"] == "59.48%"
    app.multiselect(key="geo_countries").set_value([]).run()
    assert app.dataframe[0].value.set_index("Country / region").equals(all_values)
    app.multiselect(key="geo_countries").set_value(selected).run()
    assert values.loc["United States", "Global share"] == "59.48%"

    # Moving to a period with Czech records must update its values immediately.
    app.selectbox(key="geo_period").set_value(0).run()
    assert not app.exception
    assert app.table[0].value.loc["Czechia", "Associated models"] == 2
    app.selectbox(key="geo_period").set_value(2).run()
    app.multiselect(key="geo_countries").set_value(["Czechia"]).run()
    assert not app.exception
    assert app.table[0].value.index.tolist() == ["Czechia"]
    assert app.table[0].value.loc["Czechia", "Global share"] == "0.00%"

    # No records anywhere in the chosen period means an undefined share, not zero.
    app.slider[0].set_value((2011, 2015)).run()
    assert not app.exception
    assert app.table[0].value.loc["Czechia", "Global share"] == "No data"


def test_accessibility_uses_the_same_leading_or_selected_countries():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()

    def country_accessibility():
        return next(frame.value.set_index("Country / region") for frame in app.dataframe
                    if "Open-weight share" in frame.value.columns)

    assert not app.exception
    assert country_accessibility().index.tolist() == app.table[0].value.index.tolist()
    assert len(country_accessibility()) == 5
    details = next(section for section in app.expander if section.label == "Accessibility and counting")
    assert len(details.metric) == 3
    categories = details.dataframe[0].value.set_index("Model accessibility")["Model records"]
    assert categories.loc[categories.index.str.startswith("Open weights")].sum() == 225

    app.radio(key="geo_mode").set_value("Select countries").run()
    selected = ["United States", "China", "Australia", "Czechia"]
    app.multiselect(key="geo_countries").set_value(selected).run()
    assert not app.exception
    values = country_accessibility()
    assert values.index.tolist() == selected == app.table[0].value.index.tolist()
    assert values.loc["United States", "Open weights"] == 131
    assert values.loc["Czechia", "Total models"] == 0
    assert values.loc["Czechia", "Open-weight share"] == "No data"
    app.selectbox(key="geo_period").set_value(0).run()
    assert not app.exception
    assert country_accessibility().loc["Czechia", "Total models"] == 2
