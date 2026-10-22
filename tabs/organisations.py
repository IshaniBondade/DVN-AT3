import altair as alt
import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
START_YEAR = 2015          # first year shown on the chart
LINE_COLOUR = "#4C8DFF"    # matches the app theme's primary colour
MUTED_COLOUR = "#8A94A8"   # used for the partial year

# Slider options: exponent -> label. Each step is 10x more training compute.
THRESHOLDS = {
    22: "10²² FLOP · broad",
    23: "10²³ FLOP · GPT-3 scale",
    24: "10²⁴ FLOP · GPT-3.5 scale",
    25: "10²⁵ FLOP · GPT-4 scale, EU AI Act line",
}


# ---------------------------------------------------------------------------
# Data transformation (this is what gets traced in the video)
# ---------------------------------------------------------------------------
def count_orgs_per_year(df, threshold):
    """
    1. keep models with training compute >= threshold
    2. drop rows where the organisation is 'Unknown'
    3. count distinct lead organisations ('org') and models per year
    4. fill years with no qualifying models with 0
    """
    frontier = df[(df["compute_flop"] >= threshold) & (df["org"] != "Unknown")]

    counts = frontier.groupby("year").agg(
        n_organisations=("org", "nunique"),
        n_models=("model", "count"),
    )

    # Show every year in range, including years where nobody qualified (0)
    first = max(START_YEAR, int(df["year"].min()))
    last = int(df["year"].max())
    counts = counts.reindex(range(first, last + 1), fill_value=0)
    counts = counts.rename_axis("year").reset_index()

    # Mark the partial (unfinished) year so it isn't read as a real drop
    partial_years = set(df.loc[df["partial_year"], "year"])
    counts["status"] = counts["year"].apply(
        lambda y: "Partial year" if y in partial_years else "Full year"
    )
    return frontier[frontier["year"] >= first], counts


def build_chart(counts):
    """Solid line for full years, dashed + hollow point for the partial year."""
    full = counts[counts["status"] == "Full year"]
    partial = counts[counts["status"] == "Partial year"]

    # The dashed segment joins the last full year to the partial year
    dashed = pd.concat([full.tail(1), partial])

    x = alt.X("year:O", title=None, axis=alt.Axis(labelAngle=0))
    y = alt.Y(
        "n_organisations:Q",
        title="Distinct organisations",
        axis=alt.Axis(tickMinStep=1, format="d"),
        scale=alt.Scale(zero=True),
    )
    tooltip = [
        alt.Tooltip("year:O", title="Year"),
        alt.Tooltip("n_organisations:Q", title="Organisations"),
        alt.Tooltip("n_models:Q", title="Models"),
        alt.Tooltip("status:N", title="Data"),
    ]

    solid_line = alt.Chart(full).mark_line(color=LINE_COLOUR, strokeWidth=3).encode(x=x, y=y)
    dashed_line = alt.Chart(dashed).mark_line(
        color=MUTED_COLOUR, strokeWidth=2, strokeDash=[6, 4]
    ).encode(x=x, y=y)
    full_points = alt.Chart(full).mark_circle(color=LINE_COLOUR, size=70).encode(
        x=x, y=y, tooltip=tooltip
    )
    partial_points = alt.Chart(partial).mark_point(
        color=MUTED_COLOUR, size=70, filled=False, strokeWidth=2
    ).encode(x=x, y=y, tooltip=tooltip)

    # Value labels above each point make exact numbers readable without hovering
    labels = alt.Chart(counts).mark_text(dy=-14, fontSize=12, color="#C9D3E6").encode(
        x=x, y=y, text="n_organisations:Q"
    )

    return (
        (solid_line + dashed_line + full_points + partial_points + labels)
        .properties(height=400)
        .configure_view(strokeWidth=0)
        .configure_axis(grid=True, gridOpacity=0.15, domain=False)
    )


# ---------------------------------------------------------------------------
# Tab layout
# ---------------------------------------------------------------------------
def render(df, df_all):
    # df = filtered data (global filters applied), df_all = unfiltered data.
    st.header("Organisations over Time")
    st.markdown(
        "**How many different organisations build frontier models each year?** "
        "If the count is falling, frontier AI is concentrating. If it is rising, it is spreading out."
    )

    # Interaction: the viewer decides how big a model must be to count as "frontier"
    exponent = st.select_slider(
        "How much training compute counts as 'frontier'?",
        options=list(THRESHOLDS),
        value=23,
        format_func=lambda e: THRESHOLDS[e],
        key="orgs_threshold",
        help="FLOP = the number of calculations used to train a model. "
        "Each step is 10× more compute. 10²⁵ FLOP is the level at which the EU AI Act "
        "presumes a model has systemic risk.",
    )

    frontier, counts = count_orgs_per_year(df, 10 ** exponent)
    full = counts[counts["status"] == "Full year"]

    if full["n_organisations"].sum() == 0:
        st.warning("No models match the current filters at this threshold.")
        return

    # Key numbers for the current threshold
    latest = full.iloc[-1]
    peak = full.loc[full["n_organisations"].idxmax()]
    baseline_year = int(latest["year"]) - 5
    baseline = full[full["year"] == baseline_year]
    baseline_n = int(baseline["n_organisations"].iloc[0]) if not baseline.empty else None

    k1, k2, k3 = st.columns(3)
    k1.metric(f"Organisations in {int(latest['year'])}", int(latest["n_organisations"]))
    k2.metric(f"Peak ({int(peak['year'])})", int(peak["n_organisations"]))
    if baseline_n is not None:
        k3.metric(
            f"Change since {baseline_year}",
            f"{int(latest['n_organisations']) - baseline_n:+d}",
        )

    # Plain-English takeaway that updates with the slider
    if baseline_n is not None:
        st.markdown(
            f"At **{THRESHOLDS[exponent].split(' · ')[0]}**, "
            f"**{int(latest['n_organisations'])} organisations** released a frontier model in "
            f"{int(latest['year'])}, compared with **{baseline_n}** in {baseline_year}."
        )

    # Chart
    with st.container(border=True):
        st.markdown(
            f"**Distinct organisations releasing models at or above "
            f"{THRESHOLDS[exponent].split(' · ')[0]}, per year**"
        )
        st.altair_chart(build_chart(counts))
        st.caption(
            "Dashed, hollow point = partial year (data to the latest Epoch AI update), not a real drop. "
            "About half of models do not report training compute and are excluded, so counts are a lower bound. "
            "Organisation = lead organisation, related names merged (e.g. Google includes DeepMind). "
            "Source: Epoch AI, 'Data on AI models' (data/processed/models_clean.csv), CC BY 4.0."
        )

    # Verification helper: the rows behind any year's number
    with st.expander("Show the data behind a number"):
        years = counts.loc[counts["n_organisations"] > 0, "year"].tolist()
        default_year = int(latest["year"])
        year = st.selectbox(
            "Year", years, index=years.index(default_year), key="orgs_year"
        )
        rows = frontier[frontier["year"] == year].sort_values(["org", "pub_date"])
        rows = rows.assign(pub_date=pd.to_datetime(rows["pub_date"]))  # works whether dates are text or dates
        st.markdown(
            f"**{year}: {rows['org'].nunique()} distinct organisations** across {len(rows)} models"
        )
        st.dataframe(
            rows[["model", "org", "pub_date", "compute_flop"]],
            hide_index=True,
            column_config={
                "model": "Model",
                "org": "Organisation",
                "pub_date": st.column_config.DateColumn("Published", format="YYYY-MM-DD"),
                "compute_flop": st.column_config.NumberColumn("Training compute (FLOP)", format="%.2e"),
            },
        )