import altair as alt
import pandas as pd
import streamlit as st
from theme import BLUE, ORANGE, MUTED, SUBTLE, callout, card_header, style_chart

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
START_YEAR = 2015          # first year shown on the charts
GRID = "#1C2840"           # same gridline colour as the Compute tab

# Slider options: exponent -> label. Each step is 10x more training compute.
THRESHOLDS = {
    22: "10²² FLOP · broad",
    23: "10²³ FLOP · GPT-3 scale",
    24: "10²⁴ FLOP · GPT-3.5 scale",
    25: "10²⁵ FLOP · GPT-4 scale, EU AI Act line",
}


def short(exponent):
    """'10²³ FLOP' without the description."""
    return THRESHOLDS[exponent].split(" · ")[0]


# ---------------------------------------------------------------------------
# Data transformation (this is what gets traced in the video)
# ---------------------------------------------------------------------------
def frontier_models(df, threshold):
    """Keep models with training compute >= threshold and a known organisation."""
    return df[(df["compute_flop"] >= threshold) & (df["org"] != "Unknown")]


def count_orgs_per_year(df, df_all, threshold):
    """
    1. keep models with training compute >= threshold
    2. drop rows where the organisation is 'Unknown'
    3. count distinct lead organisations ('org') and models per year
    4. split organisations into newcomers (first frontier model ever that year) and returning
    5. fill years with no qualifying models with 0
    """
    frontier = frontier_models(df, threshold)

    # "First frontier year" uses the UNFILTERED data, so narrowing the year slider
    # cannot make an old player look new (e.g. Google in 2020 if the range starts in 2020).
    first_year = frontier_models(df_all, threshold).groupby("org")["year"].min()
    frontier = frontier.assign(first_year=frontier["org"].map(first_year))
    frontier = frontier.assign(is_new=frontier["year"] == frontier["first_year"])

    per_org = frontier.drop_duplicates(["year", "org"])
    counts = frontier.groupby("year").agg(
        n_organisations=("org", "nunique"),
        n_models=("model", "count"),
    )
    counts["n_new"] = per_org[per_org["is_new"]].groupby("year")["org"].nunique()
    counts["new_names"] = (per_org[per_org["is_new"]].sort_values("org")
                           .groupby("year")["org"].agg(", ".join))

    # Show every year in range, including years where nobody qualified (0)
    first = max(START_YEAR, int(df["year"].min()))
    last = int(df["year"].max())
    counts = counts.reindex(range(first, last + 1))
    counts[["n_organisations", "n_models", "n_new"]] = (
        counts[["n_organisations", "n_models", "n_new"]].fillna(0).astype(int))
    counts["new_names"] = counts["new_names"].fillna("–")
    counts["n_returning"] = counts["n_organisations"] - counts["n_new"]
    counts = counts.rename_axis("year").reset_index()

    # Mark the partial (unfinished) year so it isn't read as a real drop
    partial_years = set(df_all.loc[df_all["partial_year"], "year"])
    counts["partial"] = counts["year"].isin(partial_years)
    counts["status"] = counts["partial"].map({True: "Partial year", False: "Full year"})
    counts["year_label"] = counts.apply(
        lambda r: f"{r.year}*" if r.partial else str(r.year), axis=1)
    return frontier[frontier["year"] >= first], counts


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------
def x_axis(counts):
    return alt.X("year_label:O", title=None, sort=counts["year_label"].tolist(),
                 axis=alt.Axis(labelAngle=0))


def count_chart(counts):
    """Chart 1: solid line for full years, dashed + hollow point for the partial year."""
    full = counts[~counts["partial"]]
    partial = counts[counts["partial"]]
    dashed = pd.concat([full.tail(1), partial])   # joins the last full year to the partial year

    x = x_axis(counts)
    y = alt.Y("n_organisations:Q", title="Distinct organisations", scale=alt.Scale(zero=True),
              axis=alt.Axis(tickMinStep=1, format="d", grid=True, gridColor=GRID))
    tooltip = [
        alt.Tooltip("year_label:N", title="Year"),
        alt.Tooltip("n_organisations:Q", title="Organisations"),
        alt.Tooltip("n_models:Q", title="Models"),
        alt.Tooltip("status:N", title="Data"),
    ]

    solid_line = alt.Chart(full).mark_line(color=BLUE, strokeWidth=3).encode(x=x, y=y)
    dashed_line = alt.Chart(dashed).mark_line(
        color=SUBTLE, strokeWidth=2, strokeDash=[6, 4]).encode(x=x, y=y)
    full_points = alt.Chart(full).mark_circle(color=BLUE, size=80, opacity=1).encode(
        x=x, y=y, tooltip=tooltip)
    partial_points = alt.Chart(partial).mark_point(
        color=SUBTLE, size=80, filled=False, strokeWidth=2).encode(x=x, y=y, tooltip=tooltip)
    labels = alt.Chart(counts).mark_text(dy=-16, fontSize=13, fontWeight="bold", color="#C9D8F5").encode(
        x=x, y=y, text="n_organisations:Q")

    return style_chart(solid_line + dashed_line + full_points + partial_points + labels, height=380)


def entrants_chart(counts):
    """
    Chart 2: newcomers vs returning organisations, stacked.
    Newcomers sit on the baseline so they can be compared year to year.
    """
    long = counts.melt(
        id_vars=["year", "year_label", "partial", "new_names", "n_organisations"],
        value_vars=["n_new", "n_returning"], var_name="group", value_name="n")
    long["group"] = long["group"].map({"n_new": "Newcomers", "n_returning": "Returning"})
    long["stack_order"] = long["group"].map({"Newcomers": 0, "Returning": 1})

    x = x_axis(counts)
    y = alt.Y("n:Q", title="Organisations", stack="zero",
              axis=alt.Axis(tickMinStep=1, format="d", grid=True, gridColor=GRID))
    colour = alt.Color("group:N", title=None,
                       scale=alt.Scale(domain=["Newcomers", "Returning"], range=[ORANGE, MUTED]))
    tooltip = [
        alt.Tooltip("year_label:N", title="Year"),
        alt.Tooltip("group:N", title="Group"),
        alt.Tooltip("n:Q", title="Organisations"),
        alt.Tooltip("new_names:N", title="Newcomers this year"),
    ]

    bars = alt.Chart(long).mark_bar(cornerRadiusEnd=3, size=34).encode(
        x=x, y=y, color=colour, order=alt.Order("stack_order:Q"), tooltip=tooltip,
        opacity=alt.condition("datum.partial", alt.value(0.45), alt.value(1)))

    # Number of newcomers printed inside the orange segment (only where there is room)
    new_only = long[(long["group"] == "Newcomers") & (long["n"] >= 2)]
    new_labels = alt.Chart(new_only).mark_text(dy=12, fontSize=12, fontWeight="bold", color="#0A0F1A").encode(
        x=x, y=alt.Y("n:Q"), text="n:Q")

    # Total on top of each bar, so the two charts can be read against each other
    totals = alt.Chart(counts[counts["n_organisations"] > 0]).mark_text(
        dy=-10, fontSize=13, fontWeight="bold", color="#C9D8F5").encode(
        x=x, y="n_organisations:Q", text="n_organisations:Q")

    return style_chart(bars + new_labels + totals, height=340)


# ---------------------------------------------------------------------------
# Tab layout
# ---------------------------------------------------------------------------
def render(df, df_all):
    # df = filtered data (global filters applied), df_all = unfiltered data.
    st.markdown(
        "**How many different organisations build frontier models each year, and are new ones still getting in?** "
        "A falling count, or fewer newcomers, would point to concentration. A rising count with steady "
        "newcomers would point to a field that is spreading out."
    )

    # Interaction: the viewer decides how big a model must be to count as "frontier"
    exponent = st.columns([2, 1])[0].select_slider(
        "How much training compute counts as 'frontier'?",
        options=list(THRESHOLDS),
        value=23,
        format_func=lambda e: THRESHOLDS[e],
        key="orgs_threshold",
        help="FLOP = the number of calculations used to train a model. "
        "Each step is 10× more compute. 10²⁵ FLOP is the level at which the EU AI Act "
        "presumes a model has systemic risk.",
    )

    # Guard: the global filters can leave no rows at all (e.g. every sector removed)
    if df.empty:
        st.warning("No models match the current filters. Widen the year range or add a sector.")
        return

    frontier, counts = count_orgs_per_year(df, df_all, 10 ** exponent)
    full = counts[~counts["partial"]]

    if full["n_organisations"].sum() == 0:
        st.warning(f"No models at or above {short(exponent)} match the current filters. "
                   "Lower the threshold or widen the filters above.")
        return

    # Key numbers for the current threshold
    latest = full.iloc[-1]
    latest_year = int(latest["year"])
    peak = full.loc[full["n_organisations"].idxmax()]
    peak_new = full.loc[full["n_new"].idxmax()]
    base = full[full["year"] == latest_year - 5]
    base_n = int(base["n_organisations"].iloc[0]) if not base.empty else None

    # Plain-English headline that rewrites itself for the slider and filters
    n_latest = int(latest["n_organisations"])
    if n_latest == 0:
        last_active = int(full.loc[full["n_organisations"] > 0, "year"].max())
        headline = (f"At <b>{short(exponent)}</b>, no organisation in this selection released a frontier model "
                    f"in {latest_year}. The most recent year with one was <b>{last_active}</b>.")
    else:
        headline = (f"At <b>{short(exponent)}</b>, <b>{n_latest} organisation{'s' if n_latest != 1 else ''}</b> "
                    f"released a frontier model in {latest_year}")
        if base_n is None:
            headline += "."
        elif n_latest > base_n:
            headline += f", up from <b>{base_n}</b> in {latest_year - 5}."
        elif n_latest < base_n:
            headline += f", down from <b>{base_n}</b> in {latest_year - 5}."
        else:
            headline += f", the same as in {latest_year - 5}."
        # Only add the newcomer point when it is actually true: fewer newcomers than at the peak,
        # and returning organisations now outnumber them
        if (int(peak_new["n_new"]) > int(latest["n_new"])
                and int(latest["n_returning"]) > int(latest["n_new"])):
            headline += (f" But newcomers peaked at <b>{int(peak_new['n_new'])}</b> in {int(peak_new['year'])} "
                         f"and were <b>{int(latest['n_new'])}</b> in {latest_year}: more of the frontier is now "
                         "the same organisations returning.")
    callout(headline)

    k1, k2, k3, k4 = st.columns(4)
    # Every card gets a grey sub-label so the four cards are the same height
    k1.metric(f"Frontier orgs, {latest_year}", int(latest["n_organisations"]), f"at {short(exponent)}",
              delta_color="off", delta_arrow="off")
    k2.metric("Peak", int(peak["n_organisations"]), f"in {int(peak['year'])}",
              delta_color="off", delta_arrow="off")
    if base_n is not None:
        k3.metric(f"Change since {latest_year - 5}", f"{int(latest['n_organisations']) - base_n:+d}",
                  f"from {base_n} organisations", delta_color="off", delta_arrow="off")
    k4.metric(f"Newcomers, {latest_year}", int(latest["n_new"]),
              f"peak {int(peak_new['n_new'])} in {int(peak_new['year'])}",
              delta_color="off", delta_arrow="off")

    # ---------- chart 1: how many organisations ----------
    with st.container(border=True):
        card_header(f"Organisations releasing models at or above {short(exponent)}, per year",
                    "Each point counts distinct lead organisations that year. Move the slider above to "
                    "change what counts as frontier.")
        st.altair_chart(count_chart(counts), theme=None, width="stretch")
        st.caption("\\* and dashed line = partial year (data to the latest Epoch AI update), not a real drop. "
                   "About half of models do not report training compute and are excluded, so counts are a "
                   "lower bound. Related names merged (Google includes DeepMind).")

    # ---------- chart 2: newcomers vs returning ----------
    with st.container(border=True):
        card_header("Are new organisations still reaching the frontier?",
                    "Each bar splits that year's organisations into newcomers (their first ever model at this "
                    "scale, in orange) and returning organisations (grey). Hover to see the newcomers' names.")
        st.altair_chart(entrants_chart(counts), theme=None, width="stretch")
        st.caption("Newcomer = first model at or above this threshold in the whole dataset, regardless of the "
                   "year filter, so an established lab never counts as new. Faded bar = partial year.")

    # ---------- verification helper ----------
    with st.expander("Show the data behind a number"):
        # Only offer years that have data; open on the most recent one.
        # (The latest full year may have no data under some filters, e.g. Academia only.)
        years = counts.loc[counts["n_organisations"] > 0, "year"].tolist()
        year = st.selectbox("Year", years, index=len(years) - 1, key="orgs_year")
        rows = frontier[frontier["year"] == year].sort_values(["org", "pub_date"])
        rows = rows.assign(pub_date=pd.to_datetime(rows["pub_date"]))  # works whether dates are text or dates
        st.markdown(
            f"**{year}: {rows['org'].nunique()} distinct organisations** across {len(rows)} models, "
            f"of which **{rows.loc[rows['is_new'], 'org'].nunique()}** were newcomers"
        )
        st.dataframe(
            rows[["model", "org", "pub_date", "compute_flop", "first_year"]],
            hide_index=True,
            column_config={
                "model": "Model",
                "org": "Organisation",
                "pub_date": st.column_config.DateColumn("Published", format="YYYY-MM-DD"),
                "compute_flop": st.column_config.NumberColumn("Training compute (FLOP)", format="%.2e"),
                "first_year": st.column_config.NumberColumn("First frontier year", format="%d"),
            },
        )
        st.caption("Source: Epoch AI, 'Data on AI models' (data/processed/models_clean.csv), CC BY 4.0.")