"""Streamlit UI. render(models) can be embedded in the group's Geography tab."""
from __future__ import annotations

import json
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

from .charts import trend_chart, type_distribution
from .map import render_map
from .data import accessibility_by_country, country_summary, distribution_rows, domain_counts, in_period, load_models, model_details, normalize_models, shares_over_time, with_domain
from .settings import data_path, load_dashboard, load_settings

PLOT_CONFIG = {"displayModeBar": False, "scrollZoom": False, "responsive": True}


def caption(text: str) -> None:
    """Keep Geography hints small and consistent, including dynamic source labels."""
    st.markdown(
        '<p class="geo-caption" style="font-size:12px;font-style:italic;'
        'line-height:1.45;color:#8fa0bf;margin:0;">' + escape(text) + '</p>',
        unsafe_allow_html=True,
    )


def _map_values(summary: pd.DataFrame, countries: list[str] | None = None) -> pd.DataFrame:
    values = summary[["country", "share", "credit", "associated_models"]].copy()
    if countries is not None:
        values = values.set_index("country").reindex(countries).rename_axis("country").reset_index()
        values[["credit", "associated_models"]] = values[["credit", "associated_models"]].astype(float).fillna(0)
        values["associated_models"] = values["associated_models"].astype(int)
        if not summary.empty:
            values["share"] = values["share"].fillna(0)
    values["share"] = values["share"].map(lambda value: "No data" if pd.isna(value) else f"{value:.2%}")
    values["credit"] = values["credit"].map(lambda value: f"{value:.2f}")
    return values.rename(columns={"country": "Country / region", "share": "Global share",
                                  "credit": "Model credits*", "associated_models": "Associated models"})


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
    defaults = {"period": analysis["default_period"], "mode": "Leading countries", "countries": default_countries, "domain": analysis["default_type"] if analysis["default_type"] in all_domains else all_domains[0], "expanded": False, "open_details": False}
    for name, value in defaults.items():
        st.session_state.setdefault(prefix + name, value)
    if st.session_state[prefix + "domain"] not in all_domains:
        st.session_state[prefix + "domain"] = all_domains[0]
    st.session_state[prefix + "countries"] = [c for c in st.session_state[prefix + "countries"] if c in available][:analysis["max_selected_countries"]]
    if not 0 <= st.session_state[prefix + "period"] < len(periods):
        st.session_state[prefix + "period"] = analysis["default_period"]
    if show_header:
        caption("AI DATA NARRATIVE STUDIO · GEOGRAPHY")
        st.title(content["title"])
        caption(content["question"])
    with st.container(border=True):
        title_col, period_col = st.columns([2.4, 1])
        title_col.subheader(content["sections"]["map"])
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
        st.radio("Country view", ["Leading countries", "Select countries"], horizontal=True, key=prefix + "mode", label_visibility="collapsed")
        if st.session_state[prefix + "mode"] == "Select countries":
            st.multiselect("Choose countries / regions", available, max_selections=analysis["max_selected_countries"], key=prefix + "countries", placeholder="Choose up to four countries")
            if not selected:
                st.info("Choose at least one country below the map, or switch to Leading countries.")
        known_count = int(snapshot["countries"].map(len).gt(0).sum())
        missing = len(snapshot) - known_count
        caption(f"{len(snapshot):,} models" + (f" · {missing:,} without country data (excluded from shares)" if missing else ""))
        if not known_count:
            st.warning("No known-origin records in this period. Country shares are unavailable.")
        mapped = {feature["properties"]["id"] for feature in geometry["features"]}
        omitted = [c for c in summary["country"] if codes.get(c) not in mapped]
        if omitted:
            caption("Counted, not mapped: " + ", ".join(omitted) + ".")
        # Selected values retain zero-record countries; the full table ignores selection.
        values = _map_values(summary, selected)
        shown_values = values.head(analysis["leading_countries"]) if selected is None else values
        shown_countries = shown_values["Country / region"].tolist()
        credit_note = "* Each model contributes 1 credit, divided equally among its listed developer countries."
        if not shown_values.empty:
            st.markdown("**Leading country values**" if selected is None else "**Selected country values**")
            st.table(shown_values.set_index("Country / region"))
            caption(credit_note)
        all_countries = sorted(set(available) | set(summary["country"]))
        all_values = _map_values(summary, all_countries)
        if not all_values.empty:
            with st.expander("All map values"):
                st.dataframe(all_values, hide_index=True, width="stretch")
                caption(credit_note)
    left, right = st.columns([.85, 1.15], gap="medium")
    latest = in_period(models, *periods[-1])
    leaders = country_summary(latest)
    leaders = leaders.loc[leaders["country"].ne("Multinational"), "country"].head(3).tolist()
    compare = leaders if selected is None else selected
    with left, st.container(border=True):
        st.subheader(content["sections"]["trend"])
        caption(f"{periods[-1][0]}–{periods[-1][1]} leaders + all other origins" if selected is None else "Selected countries + all other origins")
        trend = shares_over_time(models, periods, compare)
        st.plotly_chart(trend_chart(trend, compare, periods, period_index), use_container_width=True, theme=None, config=PLOT_CONFIG, key=prefix + "trend", on_select=lambda: _select_period(prefix), selection_mode="points")
        caption(f"{period_label} · Click a bar to change period")
        period_labels = [f"{a}–{b}" for a, b in periods]
        trend_values = trend.pivot(index="country", columns="period", values="share").reindex(
            index=[*compare, "Other origins"], columns=period_labels)
        trend_values = trend_values.apply(lambda column: column.map(
            lambda value: "No data" if pd.isna(value) else f"{value:.1%}"))
        trend_values.index.name = "Country / region"
        trend_values.columns.name = None
        caption("Global share (%) · No data = no known origins")
        st.table(trend_values)
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
        caption(f"{period_label} · Select an AI type")
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
        caption(f"{len(type_models):,} models · {type_known:,} with country data")
        if type_summary.empty:
            st.info("No models with known origins for this type in this period.")
        else:
            expanded = st.session_state[prefix + "expanded"]
            shown = distribution_rows(type_summary, selected=selected, limit=None if expanded else analysis["leading_countries"])
            st.plotly_chart(type_distribution(shown, domain), use_container_width=True, theme=None, config=PLOT_CONFIG, key=prefix + "distribution", on_select=lambda: _select_country(prefix), selection_mode="points")
            if selected is None and len(type_summary) > analysis["leading_countries"]:
                st.checkbox(f"Show all {len(type_summary)} countries / regions", key=prefix + "expanded")
            caption("Click a country for models · Types overlap")
    with st.container(border=True):
        st.subheader("How are these models made available?")
        caption(f"{period_label} · all AI types")
        accessibility = accessibility_by_country(snapshot)
        shown_accessibility = accessibility.set_index("country").reindex(shown_countries)
        count_columns = ["Open weights", "Not open weights", "Unknown", "Total models"]
        shown_accessibility[count_columns] = shown_accessibility[count_columns].astype(float).fillna(0).astype(int)
        shown_accessibility["Open-weight share"] = shown_accessibility["Open-weight share"].map(
            lambda value: "No data" if pd.isna(value) else f"{value:.2%}")
        if not shown_accessibility.empty:
            st.markdown("**Leading country values**" if selected is None else "**Selected country values**")
            st.dataframe(shown_accessibility.rename_axis("Country / region").reset_index(),
                         hide_index=True, width="stretch")
        with st.expander("Accessibility and counting"):
            open_countries = int(accessibility["Open weights"].gt(0).sum())
            open_models = int(snapshot["open_weight_status"].eq("Open weights").sum())
            unknown_models = int(snapshot["open_weight_status"].eq("Unknown").sum())
            country_metric, model_metric, unknown_metric = st.columns(3)
            country_metric.metric("Countries with open-weight models", f"{open_countries} / {len(accessibility)}")
            model_metric.metric("Open-weight model records", f"{open_models:,}")
            unknown_metric.metric("Unknown weight status", f"{unknown_models:,}")
            categories = snapshot["model_accessibility"].replace("", "Unknown").value_counts()
            st.dataframe(categories.rename_axis("Model accessibility").reset_index(name="Model records"),
                         hide_index=True, width="stretch")
            caption("Weights flag first; accessibility labels fill gaps. "
                    "Open-weight share = open-weight models ÷ all models per country, including unknowns. "
                    "Joint models count in each listed country; summary totals are global.")
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
            caption(f"{len(records):,} models · Joint-country credits are split")
            display = records.rename(columns={"model": "Model / version", "organization": "Developer", "publication_date": "Published", "country": "Source origins", "domain": "AI types", "task": "Tasks", "model_accessibility": "Model accessibility", "open_weight_status": "Weight status", "country_credit": "Country credit", "link": "Source", "record_id": "Record ID", "source_record": "Source record"})
            st.dataframe(display, hide_index=True, width="stretch", height=310, column_config={"Source": st.column_config.LinkColumn("Source", display_text="Open source"), "Country credit": st.column_config.NumberColumn(format="%.4f")})
            st.download_button("Download these model records", data=records.to_csv(index=False).encode("utf-8"), file_name="geography-model-records.csv", mime="text/csv", key=prefix + "download")
    with st.expander("Source and counting method"):
        st.markdown(f"[Epoch AI notable models]({config['data']['source_url']}) · Snapshot: {config['data']['snapshot_date']}. Curated dataset; not all AI development.")
        st.markdown(
            "- Each model counts once, split equally across its listed developer countries. Country selection keeps the global denominator.\n"
            "- Missing origins excluded; Multinational included in shares. Types overlap; versions count separately.\n"
            "- Map and trend cover all types; type selection changes the type chart and model details.\n"
        )
    caption(f"Epoch AI · CC BY 4.0 · Snapshot: {config['data']['snapshot_date']}")
