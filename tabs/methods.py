import altair as alt
import pandas as pd
import streamlit as st
from common import DATA_DOWNLOADED, DATA_LATEST_OBS
from theme import BLUE, TEXT, SUBTLE, BORDER, callout, card_header, style_chart

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
RAW_PATH = "data/raw/notable_ai_models.csv"
PROCESSED_PATH = "data/processed/models_clean.csv"

# Fields checked for completeness: label -> test for "this value is present"
FIELDS = {
    "Training compute": lambda d: d["compute_flop"].notna(),
    "Parameters": lambda d: d["parameters"].notna(),
    "Accessibility": lambda d: d["accessibility"].notna(),
    "Sector": lambda d: d["sector"] != "Unknown",
    "Country": lambda d: d["country"] != "Unknown",
    "Organisation": lambda d: d["org"] != "Unknown",
}

# Time periods for the completeness heatmap (early decades have few models, so they are grouped)
PERIODS = [(1950, 1999, "1950–1999"), (2000, 2009, "2000–2009"), (2010, 2014, "2010–2014"),
           (2015, 2019, "2015–2019"), (2020, 2024, "2020–2024"), (2025, 2026, "2025–2026*")]

PIPELINE = [
    ("1 · Download", f"Epoch AI 'Notable AI Models' CSV, retrieved {DATA_DOWNLOADED}.", RAW_PATH),
    ("2 · Clean", "Rename columns, parse dates, merge parent organisations, derive sector and country.",
     "scripts/make_processed.py"),
    ("3 · Check", "Assertions: row count unchanged, unique model names, every date parses, frontier count kept.",
     "assert statements in the script"),
    ("4 · Save", "One row per model, nothing dropped, missing values left missing.", PROCESSED_PATH),
    ("5 · Filter & chart", "Year, sector and frontier filters apply to every tab.", "app.py → tabs/*.py"),
]

DEFINITIONS = [
    ("Notable model", "A model in Epoch AI's notable-models list: state of the art, highly cited, historically "
     "important or widely used. Epoch chooses what is notable, so this is not every AI model ever built."),
    ("Frontier model", "Epoch AI's own flag for models that were among the most compute-intensive when "
     "released. "
     "Shown only when 'Frontier models only' is ticked."),
    ("Training compute (FLOP)", "Total floating-point operations used to train the model. Usually an Epoch "
     "estimate, not a figure from the developer. Each 10× step is one 'order of magnitude'."),
    ("Organisation", "The first organisation listed for a model. Subsidiaries and old names are merged into "
     "their parent (table on the right), so Google includes DeepMind."),
    ("Sector", "Industry, Academia, Industry + Academia (a collaboration), Other, or Unknown, from Epoch's "
     "organisation categorisation."),
    ("Country", "Headquarters country of the first-listed organisation."),
    ("Partial year", f"The latest year in the data only runs to {DATA_LATEST_OBS}. Charts mark it so it is "
     "not read as a real drop."),
]


# ---------------------------------------------------------------------------
# Data transformation
# ---------------------------------------------------------------------------
def completeness(df):
    """
    For each field and time period: % of models where that field is present.
    Returns long format (field, period, pct, n) for the heatmap.
    """
    rows = []
    for start, end, label in PERIODS:
        g = df[df["year"].between(start, end)]
        for field, present in FIELDS.items():
            rows.append({"field": field, "period": label, "n": len(g),
                         "pct": present(g).mean() * 100 if len(g) else None})
    return pd.DataFrame(rows)


def alias_table(df_all):
    """Rows where the first-listed raw organisation was merged into a parent name."""
    first = df_all["org_raw"].fillna("").str.split(",").str[0].str.strip()
    merged = df_all[(first != df_all["org"]) & (df_all["org"] != "Unknown")]
    return (merged.assign(raw_name=first[merged.index])
            .groupby(["org", "raw_name"]).size().rename("models").reset_index()
            .sort_values(["org", "models"], ascending=[True, False]))


def run_checks(df_all):
    """The same checks as scripts/make_processed.py, re-run on the file the app loads."""
    years = df_all["year"]
    return [
        ("Every model name is unique (primary key)", df_all["model"].is_unique,
         f"{df_all['model'].nunique():,} unique of {len(df_all):,}"),
        ("Every publication date parsed", bool(df_all["pub_date"].notna().all()),
         f"{df_all['pub_date'].min():%d %b %Y} to {df_all['pub_date'].max():%d %b %Y}"),
        ("Training compute is never zero or negative", bool((df_all["compute_flop"].dropna() > 0).all()),
         f"smallest {df_all['compute_flop'].min():.0f} FLOP"),
        ("compute_reported matches compute_flop", bool((df_all["compute_reported"] == df_all["compute_flop"].notna()).all()),
         f"{int(df_all['compute_reported'].sum()):,} models report compute"),
        ("Only the latest year is flagged partial", set(years[df_all["partial_year"]]) == {years.max()},
         f"{int(df_all['partial_year'].sum())} models in {years.max()}"),
        ("'Unknown' organisation only where the raw file lists none",
         bool(((df_all["org"] == "Unknown") == (df_all["n_orgs"] == 0)).all()),
         f"{int((df_all['org'] == 'Unknown').sum())} models"),
    ]


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------
def completeness_chart(comp):
    order = list(FIELDS)
    periods = [p[2] for p in PERIODS]
    base = alt.Chart(comp.dropna(subset=["pct"])).encode(
        x=alt.X("period:O", title=None, sort=periods, axis=alt.Axis(labelAngle=0, orient="top")),
        y=alt.Y("field:N", title=None, sort=order),
    )
    tiles = base.mark_rect(cornerRadius=6, stroke="#0A0F1A", strokeWidth=3).encode(
        color=alt.Color("pct:Q", title="% of models with this field",
                        scale=alt.Scale(domain=[0, 100], range=["#151C2C", BLUE]),
                        legend=alt.Legend(orient="bottom", gradientLength=320, format=".0f")),
        tooltip=[alt.Tooltip("field:N", title="Field"), alt.Tooltip("period:N", title="Period"),
                 alt.Tooltip("pct:Q", title="% present", format=".0f"),
                 alt.Tooltip("n:Q", title="Models in period")],
    )
    labels = base.mark_text(fontSize=14, fontWeight="bold", color=TEXT).encode(
        text=alt.Text("pct:Q", format=".0f"))
    return style_chart(tiles + labels, height=46 * len(order) + 70)


def pipeline_html():
    steps = "".join(
        f'<div style="flex:1;min-width:170px;background:#131C2E;border:1px solid {BORDER};border-radius:14px;'
        f'padding:14px 16px;"><div style="color:{BLUE};font-weight:700;font-size:.95rem">{title}</div>'
        f'<div style="color:{TEXT};font-size:.88rem;margin:6px 0 8px 0">{desc}</div>'
        f'<code style="font-size:.75rem;color:{SUBTLE};background:none;padding:0">{file}</code></div>'
        for title, desc, file in PIPELINE)
    return f'<div style="display:flex;gap:10px;flex-wrap:wrap;margin:4px 0 6px 0">{steps}</div>'


# ---------------------------------------------------------------------------
# Tab layout
# ---------------------------------------------------------------------------
def render(df, df_all):
    # df = filtered data (global filters applied), df_all = unfiltered data.
    st.markdown("**Where every number in this app comes from, what we did to it, and what it cannot tell you.** "
                "Every chart reads one file, built from one public source by one script.")

    multi_share = (df_all["n_orgs"] > 1).mean() * 100
    compute_share = df_all["compute_reported"].mean() * 100
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Models in the dataset", f"{len(df_all):,}",
              f"{df_all['year'].min()}–{df_all['year'].max()}", delta_color="off", delta_arrow="off")
    k2.metric("In current selection", f"{len(df):,}",
              f"{len(df) / len(df_all) * 100:.0f}% of all models", delta_color="off", delta_arrow="off")
    k3.metric("Report training compute", f"{compute_share:.0f}%",
              f"{int(df_all['compute_reported'].sum()):,} models", delta_color="off", delta_arrow="off")
    k4.metric("Built by more than one organisation", f"{multi_share:.0f}%",
              "credited to the first-listed only", delta_color="off", delta_arrow="off")

    # ---------- source ----------
    with st.container(border=True):
        card_header("Source", "One public dataset, used under its open licence.")
        c1, c2 = st.columns([3, 2])
        c1.markdown(
            "**Epoch AI, *Data on AI models* (Notable AI Models)**  \n"
            "[epoch.ai/data/ai-models](https://epoch.ai/data/ai-models) · Licence: CC BY 4.0  \n"
            f"Downloaded **{DATA_DOWNLOADED}** · Latest model in data: **{DATA_LATEST_OBS}**  \n"
            f"Raw file: `{RAW_PATH}` · Cleaned file: `{PROCESSED_PATH}`")
        c2.markdown(
            "**Why Epoch AI?** It is the most widely cited open record of AI models, with compute, organisation, "
            "sector and country for each one, and it documents how each estimate was made.")

    # ---------- pipeline ----------
    with st.container(border=True):
        card_header("From download to chart", "Nothing is edited by hand. Re-running the script rebuilds the "
                    "cleaned file exactly.")
        st.markdown(pipeline_html(), unsafe_allow_html=True)
        st.code("pip install -r requirements.txt\npython scripts/make_processed.py   # rebuilds the cleaned file\n"
                "streamlit run app.py", language="bash")

    # ---------- completeness ----------
    comp = completeness(df)
    with st.container(border=True):
        card_header("How complete is the data?",
                    "Share of models where each field is filled in, by period (current filters). "
                    "Darker = more missing, brighter = more complete. * = partial year.")
        st.altair_chart(completeness_chart(comp), theme=None, width="stretch")
        # Reporting trend over the last few full and partial years (unfiltered, so it does not jump with filters)
        by_year = df_all[df_all["year"] >= df_all["year"].max() - 3].groupby("year")["compute_reported"].mean() * 100
        first, last = by_year.index.min(), by_year.index.max()
        callout(f"<b>Training compute is the weakest field, and getting weaker.</b> {by_year[first]:.0f}% of "
                f"{first} models report it, falling to {by_year[last]:.0f}% of {last} models. Compute-based "
                "charts therefore cover a shrinking share of recent models, and the Compute and Organisations "
                "tabs say how many they leave out.")

    # ---------- definitions & judgement calls ----------
    c1, c2 = st.columns([3, 2])
    with c1:
        with st.container(border=True):
            card_header("Definitions", "What each term means everywhere in this app.")
            for term, meaning in DEFINITIONS:
                st.markdown(f"**{term}.** {meaning}")
    with c2:
        with st.container(border=True):
            card_header("Organisations we merged",
                        "First-listed raw name → parent. Without this, Google's share would be split "
                        "across five names and understated.")
            aliases = alias_table(df_all)
            st.dataframe(aliases, hide_index=True, width="stretch", height=420,
                         column_config={"org": "Counted as", "raw_name": "Name in raw file",
                                        "models": st.column_config.NumberColumn("Models", format="%d")})

    # ---------- limitations ----------
    with st.container(border=True):
        card_header("What this data cannot tell you", "And how each limit affects our answer.")
        st.markdown(
            f"- **Missing compute (≈{100 - compute_share:.0f}% of models).** Compute shares use only models that "
            "report it. If the models that go unreported are mostly from big labs, true concentration is *higher* "
            "than shown; if they are mostly small, it is lower. We cannot tell which from this data.\n"
            f"- **First-listed organisation only.** {multi_share:.0f}% of models are collaborations; partners after "
            "the first get no credit. This can overstate the lead lab and understate academia.\n"
            "- **Epoch decides what is notable.** Small, private or unpublished models are missing, so counts "
            "describe the visible frontier, not all AI development.\n"
            f"- **2026 is incomplete** (data to {DATA_LATEST_OBS}). Year-on-year changes into 2026 are not real "
            "drops.\n"
            "- **Released, not used.** The data records models when published, not how widely they are used "
            "or how much revenue they earn.")

    # ---------- quality checks ----------
    with st.container(border=True):
        card_header("Data checks, re-run live", "The script's checks, repeated on the exact file this app loads.")
        for name, ok, detail in run_checks(df_all):
            icon = "✅" if ok else "❌"
            st.markdown(f"{icon} **{name}**  <span style='color:{SUBTLE}'>· {detail}</span>",
                        unsafe_allow_html=True)

    # ---------- download & citation ----------
    with st.container(border=True):
        card_header("Get the data", "Download exactly what the app is showing, to check any number yourself.")
        d1, d2 = st.columns(2)
        d1.download_button("Download current selection (CSV)", df.to_csv(index=False).encode("utf-8"),
                           file_name="models_selection.csv", mime="text/csv", width="stretch")
        d2.download_button("Download full cleaned dataset (CSV)", df_all.to_csv(index=False).encode("utf-8"),
                           file_name="models_clean.csv", mime="text/csv", width="stretch")
        st.caption("Cite the source as: Epoch AI (2026), 'Data on AI models'. Published online at epoch.ai. "
                   "Retrieved from https://epoch.ai/data/ai-models. Licence: CC BY 4.0. "
                   "Full column-by-column documentation: data/DATA_DICTIONARY.md. "
                   "AI use: AI_PROVENANCE.md and DISCLOSURE.md.")
