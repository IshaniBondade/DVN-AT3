import altair as alt
import streamlit as st

# What counts as a "frontier" model: training compute of at least 10^x FLOP
THRESHOLD_OPTIONS = [22, 23, 24, 25]
START_YEAR = 2012


def count_orgs_per_year(df, threshold):
    """The transformation behind the chart (this is what gets traced in the video):
    1. keep models from START_YEAR onwards
    2. keep models with training compute >= threshold
    3. drop rows where the organisation is 'Unknown'
    4. count distinct lead organisations ('org' column) per year
    """
    frontier = df[
        (df["year"] >= START_YEAR)
        & (df["compute_flop"] >= threshold)
        & (df["org"] != "Unknown")
    ]
    counts = (
        frontier.groupby("year")["org"]
        .nunique()
        .reset_index(name="n_organisations")
    )
    return frontier, counts


def render(df, df_all):
    # df = filtered data (global filters applied), df_all = unfiltered data.
    st.header("Organisations over Time")
    st.markdown(
        "**How many different organisations release frontier models each year?** "
        "If this number is falling, frontier AI is concentrating. If it is rising, it is spreading out."
    )

    # Interaction: the user decides what counts as "frontier"
    threshold_exp = st.select_slider(
        "Frontier = training compute of at least…",
        options=THRESHOLD_OPTIONS,
        value=23,
        format_func=lambda x: f"10^{x} FLOP",
        key="orgs_threshold",
    )
    threshold = 10 ** threshold_exp

    frontier, counts = count_orgs_per_year(df, threshold)

    if counts.empty:
        st.warning("No models match the current filters and threshold.")
        return

    # Chart: line chart of distinct organisations per year
    with st.container(border=True):
        st.markdown(f"**Distinct organisations releasing models above 10^{threshold_exp} FLOP, per year**")
        chart = (
            alt.Chart(counts)
            .mark_line(point=True)
            .encode(
                x=alt.X("year:O", title="Year"),
                y=alt.Y("n_organisations:Q", title="Distinct organisations", scale=alt.Scale(zero=True)),
                tooltip=[
                    alt.Tooltip("year:O", title="Year"),
                    alt.Tooltip("n_organisations:Q", title="Organisations"),
                ],
            )
            .properties(height=420)
        )
        st.altair_chart(chart)
        st.caption(
            "2026 is a partial year, so it is not directly comparable. About half of models do not "
            "report training compute and are excluded. Organisation = lead organisation, related "
            "names merged. Source: Epoch AI, 'Data on AI models' (data/processed/models_clean.csv)."
        )

    # Verification helper: show the rows behind any year's number
    with st.expander("Show the data behind a number"):
        years = sorted(counts["year"].unique())
        year = st.selectbox("Year", years, index=len(years) - 1, key="orgs_year")
        rows = frontier[frontier["year"] == year][
            ["model", "org", "pub_date", "compute_flop"]
        ].sort_values("org")
        st.write(
            f"**{year}: {rows['org'].nunique()} distinct organisations** across {len(rows)} models"
        )
        st.dataframe(rows, hide_index=True)