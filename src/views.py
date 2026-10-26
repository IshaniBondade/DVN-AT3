"""Streamlit UI. render(models) can be embedded in the group's Geography tab."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from .charts import trend_chart, type_distribution
from .map import render_map
from .data import accessibility_by_country, country_summary, distribution_rows, domain_counts, in_period, load_models, model_details, normalize_models, shares_over_time, with_domain
from .settings import data_path, load_dashboard, load_settings

PLOT_CONFIG = {"displayModeBar": False, "scrollZoom": False, "responsive": True}


@st.cache_data(show_spinner=False)
def _read_models(path: str, mtime_ns: int, column_map: dict) -> pd.DataFrame:
    return load_models(Path(path), column_map)


@st.cache_data(show_spinner=False)
def _read_json(path: str, mtime_ns: int) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _set_domain(domain: str, prefix: str) -> None:
    st.session_state[prefix + "domain"] = domain
    st.session_state[prefix + "expanded"] = False
    st.session_state[prefix + "open_details"] = False
    st.session_state.pop(prefix + "detail_country", None)


def _select_period(prefix: str) -> None:
    points = st.session_state.get(prefix + "trend", {}).get("selection", {}).get("points", [])
    if points:
        custom = points[-1].get("customdata")
        if custom:
            st.session_state[prefix + "period"] = int(custom[0])


def _select_country(prefix: str) -> None:
    points = st.session_state.get(prefix + "distribution", {}).get("selection", {}).get("points", [])
    if points:
        custom = points[-1].get("customdata")
        if custom and custom[0] != "Other origins":
            st.session_state[prefix + "detail_country"] = custom[0]
            st.session_state[prefix + "open_details"] = True


def render(models: pd.DataFrame | None = None, *, key_prefix: str = "geo_", show_header: bool = True) -> None:
    """Render locally or inside the team's existing tab.

    Pass raw Epoch/canonical columns, or omit models to use config.toml's CSV.
    This function deliberately does not call st.set_page_config().
    """
    config, content = load_settings(), load_dashboard()
    analysis = config["analysis"]
    prefix = key_prefix
    if models is None:
        path = data_path(config, "processed")
        if not path.exists():
            st.error("Processed data is missing. Run: python -m src.pipeline build")
            return
        try:
            models = _read_models(str(path), path.stat().st_mtime_ns, config.get("columns", {}))
        except ValueError as error:
            st.error(str(error))
            return
    else:
        try:
            # A copy prevents mutations to another tab's shared DataFrame.
            models = normalize_models(models.copy(), config.get("columns"))
        except ValueError as error:
            st.error(str(error))
            return
    periods = analysis["periods"]
    covered = in_period(models, periods[0][0], periods[-1][1])
    if covered.empty:
        st.warning("No models fall in the configured analysis periods.")
        return
    all_domains = sorted({tag for tags in covered["domains"] for tag in tags})
    if not all_domains:
        st.warning("No model-type tags are available in these records.")
        return
    # Rank types by full analysis-window frequency; keep their locations stable.
    full_counts = domain_counts(covered, all_domains).sort_values(["records", "domain"], ascending=[False, True])
    all_domains = full_counts["domain"].tolist()
    available = sorted({c for cs in covered["countries"] for c in cs if c != "Multinational"})
    default_countries = [c for c in analysis["default_countries"] if c in available]
    defaults = {"period": analysis["default_period"], "mode": "All countries", "countries": default_countries, "domain": analysis["default_type"] if analysis["default_type"] in all_domains else all_domains[0], "expanded": False, "open_details": False}
    for name, value in defaults.items():
        st.session_state.setdefault(prefix + name, value)
    if st.session_state[prefix + "domain"] not in all_domains:
        st.session_state[prefix + "domain"] = all_domains[0]
    st.session_state[prefix + "countries"] = [c for c in st.session_state[prefix + "countries"] if c in available][:analysis["max_selected_countries"]]
    if not 0 <= st.session_state[prefix + "period"] < len(periods):
        st.session_state[prefix + "period"] = analysis["default_period"]
    if show_header:
        st.caption("AI DATA NARRATIVE STUDIO · GEOGRAPHY")
        st.title(content["title"])
        st.caption(content["question"])
    with st.container(border=True):
        title_col, period_col = st.columns([2.4, 1])
        title_col.subheader(content["sections"]["map"])
        title_col.caption("Hover for country shares, model counts and developer context.")
        with period_col:
            period_index = st.selectbox("Models published during", list(range(len(periods))), format_func=lambda i: f"{periods[i][0]}–{periods[i][1]}", key=prefix + "period")
        start, end = periods[period_index]
        period_label = f"{start}–{end}"
        snapshot = in_period(models, start, end)
        summary = country_summary(snapshot)
        selected = st.session_state[prefix + "countries"] if st.session_state[prefix + "mode"] == "Select countries" else None
        geometry_path, codes_path = data_path(config, "geometry"), data_path(config, "country_codes")
        geometry = _read_json(str(geometry_path), geometry_path.stat().st_mtime_ns)
        codes = _read_json(str(codes_path), codes_path.stat().st_mtime_ns)
        render_map(summary, geometry, codes, selected, period_label)
        st.caption("Darker blue = larger global share. Grey = no recorded models. Countries outside your selection are faded.")
        st.radio("Country view", ["All countries", "Select countries"], horizontal=True, key=prefix + "mode", label_visibility="collapsed")
        if st.session_state[prefix + "mode"] == "Select countries":
            st.multiselect("Choose countries / regions", available, max_selections=analysis["max_selected_countries"], key=prefix + "countries", placeholder="Choose up to four countries")
            if not selected:
                st.info("Choose at least one country below the map, or switch to All countries.")
            st.caption("Selections apply below. Percentages keep the global denominator.")
        else:
            st.caption("All countries / regions · full global distribution")
        known_count = int(snapshot["countries"].map(len).gt(0).sum())
        missing = len(snapshot) - known_count
        st.caption(f"{len(snapshot):,} model records · {known_count:,} with known origins" + (f" · {missing:,} excluded from country shares" if missing else ""))
        if not known_count:
            st.warning("No known-origin records in this period. Country shares are unavailable.")
        mapped = {feature["properties"]["id"] for feature in geometry["features"]}
        omitted = [c for c in summary["country"] if codes.get(c) not in mapped]
        if omitted:
            st.caption("Included in totals but absent from this map’s polygons: " + ", ".join(omitted) + ".")
    with st.container(border=True):
        st.subheader("Model accessibility · open weights")
        st.caption(f"{period_label} · all AI types · global country coverage")
        accessibility = accessibility_by_country(snapshot)
        open_countries = int(accessibility["Open weights"].gt(0).sum())
        open_models = int(snapshot["open_weight_status"].eq("Open weights").sum())
        unknown_models = int(snapshot["open_weight_status"].eq("Unknown").sum())
        country_metric, model_metric, unknown_metric = st.columns(3)
        country_metric.metric("Countries with open-weight models", f"{open_countries} / {len(accessibility)}")
        model_metric.metric("Open-weight model records", f"{open_models:,}")
        unknown_metric.metric("Unknown weight status", f"{unknown_models:,}")
        st.caption("A country is counted when at least one associated model has open weights. "
                   "This describes developer origins, not where users are permitted to access models. "
                   "Open weights includes unrestricted, non-commercial and restricted-use releases; it does not imply an open-source licence.")
        if unknown_models == len(snapshot):
            st.info("Weight accessibility is unavailable for this period. Supply Model accessibility or Open model weights? in the source data and rebuild the processed file.")
        shown_accessibility = accessibility if selected is None else accessibility.loc[accessibility["country"].isin(selected)]
        if not shown_accessibility.empty:
            st.dataframe(shown_accessibility.rename(columns={"country": "Country / region"}),
                         hide_index=True, width="stretch",
                         column_config={"Open-weight share": st.column_config.NumberColumn(format="percent")})
        categories = snapshot["model_accessibility"].replace("", "Unknown").value_counts()
        with st.expander("Model accessibility categories and counting method"):
            st.dataframe(categories.rename_axis("Model accessibility").reset_index(name="Model records"), hide_index=True, width="stretch")
            st.write("The explicit Open model weights? flag takes precedence. Where it is missing, labelled open-weight releases count as open; API, hosted, limited-access and unreleased models count as not open weights. Other values remain unknown. Country rows count joint models once for each associated origin, so rows can sum above the global model count. Multinational and missing origins are excluded from country coverage. Open-weight share uses all associated models, including unknown status, as its denominator. Country selection filters the table; headline counts remain global.")
    left, right = st.columns([.85, 1.15], gap="medium")
    latest = in_period(models, *periods[-1])
    leaders = country_summary(latest)
    leaders = leaders.loc[leaders["country"].ne("Multinational"), "country"].head(3).tolist()
    compare = leaders if selected is None else selected
    with left, st.container(border=True):
        st.subheader(content["sections"]["trend"])
        st.caption(f"{periods[-1][0]}–{periods[-1][1]} leaders + all other origins" if selected is None else "Selected countries + all other origins")
        trend = shares_over_time(models, periods, compare)
        st.plotly_chart(trend_chart(trend, compare, periods, period_index), use_container_width=True, theme=None, config=PLOT_CONFIG, key=prefix + "trend", on_select=lambda: _select_period(prefix), selection_mode="points")
        st.caption(f"Map period: {period_label} · click a column to change the shared period.")
        first = country_summary(in_period(models, *periods[0]))
        last = country_summary(latest)
        if compare and not first.empty and not last.empty:
            outside_first = 1 - first.loc[first["country"].isin(compare), "share"].sum()
            outside_last = 1 - last.loc[last["country"].isin(compare), "share"].sum()
            st.info(f"Other origins: {outside_first:.1%} → {outside_last:.1%}. " + ("The highlighted countries gained combined share." if outside_last < outside_first else "The highlighted countries did not gain combined share."))
        with st.expander("Why five-year periods?"):
            sample = [{"Period": f"{a}–{b}", "Model records": len(in_period(models, a, b))} for a, b in periods]
            st.write("Equal five-year windows reduce annual noise in sparse early data. They hide within-period changes and do not represent cumulative totals.")
            st.dataframe(pd.DataFrame(sample), hide_index=True, width="stretch")
    with right, st.container(border=True):
        st.subheader(content["sections"]["types"])
        st.caption(f"{period_label} · choose a type → explore its country distribution")
        counts = domain_counts(snapshot, all_domains).set_index("domain")["records"].to_dict()
        st.markdown(f"**All {len(all_domains)} AI types** · numbers are model records")
        domain = st.session_state[prefix + "domain"]
        for offset in range(0, len(all_domains), 3):
            for col, name in zip(st.columns(3), all_domains[offset:offset + 3]):
                with col:
                    st.button(f"{name} · {counts[name]}", key=prefix + "type_" + name, type="primary" if name == domain else "secondary", width="stretch", on_click=_set_domain, args=(name, prefix))
        st.divider()
        type_models = with_domain(snapshot, domain)
        type_summary = country_summary(type_models)
        st.markdown(f"**{domain} → countries**")
        type_known = int(type_models["countries"].map(len).gt(0).sum())
        st.caption(f"{len(type_models):,} model records · {type_known:,} with known origins")
        if type_summary.empty:
            st.info("No models with known origins for this type in this period.")
        else:
            expanded = st.session_state[prefix + "expanded"]
            shown = distribution_rows(type_summary, selected=selected, limit=None if expanded else analysis["leading_countries"])
            st.plotly_chart(type_distribution(shown, domain), use_container_width=True, theme=None, config=PLOT_CONFIG, key=prefix + "distribution", on_select=lambda: _select_country(prefix), selection_mode="points")
            if selected is None and len(type_summary) > analysis["leading_countries"]:
                st.checkbox(f"Show all {len(type_summary)} countries / regions", key=prefix + "expanded")
            st.caption("Click a country bar for model details. Types overlap; a model may have several tags.")
    # Details use the exact current type/period/country and expose source records.
    detail_options = type_summary["country"].tolist()
    if selected is not None:
        detail_options = [c for c in detail_options if c in selected]
    if detail_options:
        if st.session_state.get(prefix + "detail_country") not in detail_options:
            st.session_state[prefix + "detail_country"] = detail_options[0]
        with st.expander(content["sections"]["records"] + f" · {domain} · {period_label}", expanded=st.session_state[prefix + "open_details"]):
            country = st.selectbox("Country / region for model details", detail_options, key=prefix + "detail_country")
            records = model_details(snapshot, country, domain)
            numerator = float(records["country_credit"].sum())
            denominator = type_known
            st.markdown(f"**{country}: {numerator:.4f} model credits ÷ {denominator:,} known-origin {domain.lower()} records = {numerator / denominator:.1%}**")
            st.caption(f"{len(records):,} associated records. Joint-country models contribute fractions; versions are separate records.")
            display = records.rename(columns={"model": "Model / version", "organization": "Developer", "publication_date": "Published", "country": "Source origins", "domain": "AI types", "task": "Tasks", "model_accessibility": "Model accessibility", "open_weight_status": "Weight status", "country_credit": "Country credit", "link": "Source", "record_id": "Record ID", "source_record": "Source record"})
            st.dataframe(display, hide_index=True, width="stretch", height=310, column_config={"Source": st.column_config.LinkColumn("Source", display_text="Open source"), "Country credit": st.column_config.NumberColumn(format="%.4f")})
            st.download_button("Download these model records", data=records.to_csv(index=False).encode("utf-8"), file_name="geography-model-records.csv", mime="text/csv", key=prefix + "download")
    with st.expander("Source and counting method"):
        st.markdown(f"Source: [Epoch AI notable models]({config['data']['source_url']}). Bundled snapshot: {config['data']['snapshot_date']}. The dataset is curated and not a census of all AI development.")
        st.write("Each known-origin record contributes one global model credit, split equally across its distinct country/region tags. Country filters never change the global denominator. Missing origins are excluded from shares; Multinational remains in totals. Type tags overlap, but country shares within each type sum to 100%.")
        st.write("Geography follows developers’ source affiliations, not training hardware location, ownership or national capability. Map organisation labels and top developers use single-origin records only; the source does not reliably pair each organisation with each country for joint records. Aliases are not consolidated.")
        st.write("The map and time chart cover all AI types. The type selector affects only the type distribution and model details. Model versions and previews remain separate records.")
        st.json(models.attrs.get("validation", {}), expanded=False)
    st.caption("Epoch AI · CC BY 4.0 · Published world geometry · Country/region labels follow the source")
