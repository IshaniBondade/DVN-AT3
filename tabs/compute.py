import altair as alt
import numpy as np
import pandas as pd
import streamlit as st
from theme import BLUE, ORANGE, TEAL, MUTED, TEXT, SUBTLE, callout, card_header, style_chart

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
DL_START = 2010            # start of the deep learning era (split point for the two trend lines)
CONC_START = 2015          # first year on the concentration chart (earlier years have too few models)
SECTOR_COLOURS = {         # colour-blind-safe, matches theme.py
    "Industry": BLUE,
    "Academia": ORANGE,
    "Industry + Academia": TEAL,
    "Other": "#CC79A7",
    "Unknown": MUTED,
}
SUPERSCRIPT = str.maketrans("0123456789-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻")


def sci(flop):
    """9.4e26 -> '9.4 × 10²⁶' (readable on screen and in the video)."""
    exp = int(np.floor(np.log10(flop)))
    return f"{flop / 10 ** exp:.1f} × 10{str(exp).translate(SUPERSCRIPT)}"


def power_label_expr():
    """Vega expression that turns an axis value of 20 into '10²⁰'."""
    expr = "toString(datum.value)"
    for digit, sup in zip("0123456789-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻"):
        expr = f"replace({expr}, regexp('{digit}', 'g'), '{sup}')"
    return f"'10' + {expr}"


# ---------------------------------------------------------------------------
# Data transformation (this is what gets traced in the video)
# ---------------------------------------------------------------------------
def models_with_compute(df):
    """
    1. keep models that report training compute (about half do not)
    2. add log10(compute) for the log-scale chart
    3. add a decimal year (e.g. 2023.5) so the trend line uses exact dates
    """
    c = df[df["compute_flop"].notna() & (df["compute_flop"] > 0)].copy()
    pub = pd.to_datetime(c["pub_date"])
    c["log_flop"] = np.log10(c["compute_flop"])
    c["t"] = pub.dt.year + (pub.dt.dayofyear - 1) / 365.25
    c["pub_date"] = pub
    return c


def fit_trend(c, start, end):
    """
    Least-squares line through log10(compute) vs decimal year.
    slope = orders of magnitude per year; doubling time = 12 * log10(2) / slope months.
    """
    s = c[(c["t"] >= start) & (c["t"] < end)]
    if len(s) < 10:
        return None
    slope, intercept = np.polyfit(s["t"], s["log_flop"], 1)
    line = pd.DataFrame({"t": [s["t"].min(), s["t"].max()]})
    line["log_flop"] = intercept + slope * line["t"]
    line["pub_date"] = pd.to_datetime(
        (line["t"].astype(int)).astype(str)) + pd.to_timedelta((line["t"] % 1) * 365.25, unit="D")
    return {"n": len(s), "slope": slope, "doubling_months": 12 * np.log10(2) / slope, "line": line}


def concentration_by_year(c, top_n):
    """
    For each year from CONC_START:
    1. drop models whose organisation is 'Unknown'
    2. rank organisations by total training compute that year, take the top N
    3. compute share  = top N's compute / all compute that year
       model share    = top N's models  / all models that year (same models, so a fair comparison)
    """
    k = c[(c["org"] != "Unknown") & (c["year"] >= CONC_START)]
    rows = []
    for year, g in k.groupby("year"):
        by_org = g.groupby("org")["compute_flop"].sum().sort_values(ascending=False)
        top = by_org.head(top_n).index
        rows.append({
            "year": int(year),
            "Share of training compute": by_org.head(top_n).sum() / by_org.sum() * 100,
            "Share of models": g["org"].isin(top).mean() * 100,
            "top_orgs": ", ".join(top),
            "n_models": len(g),
            "partial": bool(g["partial_year"].any()),
        })
    return pd.DataFrame(rows)


def overall_shares(c, top_n, since):
    """Top N organisations by total compute since `since`: their share of compute vs of models."""
    k = c[(c["org"] != "Unknown") & (c["year"] >= since)]
    by_org = k.groupby("org")["compute_flop"].sum().sort_values(ascending=False)
    top = by_org.head(top_n).index
    return by_org.head(top_n).sum() / by_org.sum() * 100, k["org"].isin(top).mean() * 100, list(top), len(k)


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------
def scatter_chart(c, trends, highlight):
    y = alt.Y("log_flop:Q", title="Training compute (FLOP, log scale)",
              scale=alt.Scale(zero=False, nice=False,
                              domain=[np.floor(c["log_flop"].min()), np.ceil(c["log_flop"].max()) + 0.5]),
              axis=alt.Axis(labelExpr=power_label_expr(), grid=True, gridColor="#1C2840", tickMinStep=1))
    x = alt.X("pub_date:T", title=None, axis=alt.Axis(grid=False, format="%Y", labelAngle=0, tickCount=12))
    tooltip = [
        alt.Tooltip("model:N", title="Model"),
        alt.Tooltip("org:N", title="Organisation"),
        alt.Tooltip("pub_date:T", title="Published", format="%d %b %Y"),
        alt.Tooltip("flop_label:N", title="Training compute"),
        alt.Tooltip("sector:N", title="Sector"),
        alt.Tooltip("country:N", title="Country"),
    ]
    c = c.assign(flop_label=c["compute_flop"].map(lambda v: f"{sci(v)} FLOP"),
                 hl=(c["org"] == highlight) if highlight else True)

    sectors = [s for s in SECTOR_COLOURS if s in set(c["sector"])]
    colour = alt.Color("sector:N", title=None,
                       scale=alt.Scale(domain=sectors, range=[SECTOR_COLOURS[s] for s in sectors]))
    points = alt.Chart(c).mark_circle(stroke="#0A0F1A", strokeWidth=0.6).encode(
        x=x, y=y, tooltip=tooltip,
        color=alt.condition("datum.hl", colour, alt.value("#2A3550")) if highlight else colour,
        opacity=alt.condition("datum.hl", alt.value(0.95), alt.value(0.35)) if highlight else alt.value(0.8),
        size=alt.condition("datum.hl", alt.value(120), alt.value(40)) if highlight else alt.value(55),
        order=alt.Order("hl:O") if highlight else alt.Undefined,
    )

    layers = [points]
    for key, t in trends.items():
        if t is None:
            continue
        line = t["line"].assign(label=f"Doubles every {t['doubling_months']:.1f} months")
        layers.append(alt.Chart(line).mark_line(color=TEXT, strokeWidth=2.5, strokeDash=[7, 5]).encode(x=x, y=y))
        # Label sits beside the line where there are few dots: the start of the deep learning trend,
        # and the middle of the earlier one
        anchor = line.head(1) if key == "dl" else line.assign(
            t=line["t"].mean(), log_flop=line["log_flop"].mean(), pub_date=line["pub_date"].mean()).head(1)
        layers.append(alt.Chart(anchor).mark_text(
            align="right", dx=-10, dy=-16, color=TEXT, fontSize=13, fontWeight="bold"
        ).encode(x=x, y=y, text="label:N"))

    # Name the largest training run in the selection
    biggest = c.nlargest(1, "compute_flop")
    layers.append(alt.Chart(biggest).mark_text(
        align="right", dx=-9, dy=0, color=SUBTLE, fontSize=12
    ).encode(x=x, y=y, text="model:N"))

    return style_chart(alt.layer(*layers), height=500)


def concentration_chart(conc):
    long = conc.melt(id_vars=["year", "top_orgs", "n_models", "partial"],
                     value_vars=["Share of training compute", "Share of models"],
                     var_name="measure", value_name="share")
    long["year_label"] = long.apply(lambda r: f"{r.year}*" if r.partial else str(r.year), axis=1)
    x = alt.X("year_label:O", title=None, sort=list(long["year_label"].unique()), axis=alt.Axis(labelAngle=0))
    y = alt.Y("share:Q", title="Share held by the top organisations (%)", scale=alt.Scale(domain=[0, 100]),
              axis=alt.Axis(grid=True, gridColor="#1C2840", values=[0, 25, 50, 75, 100]))
    colour = alt.Color("measure:N", title=None,
                       scale=alt.Scale(domain=["Share of training compute", "Share of models"], range=[ORANGE, BLUE]))
    tooltip = [alt.Tooltip("year_label:N", title="Year"), alt.Tooltip("measure:N", title="Measure"),
               alt.Tooltip("share:Q", title="Share %", format=".0f"),
               alt.Tooltip("top_orgs:N", title="Top organisations"),
               alt.Tooltip("n_models:Q", title="Models with known compute")]

    # Shaded gap between the two lines = how much more concentrated compute is than model count
    wide = conc.assign(year_label=long.drop_duplicates("year")["year_label"].values)
    gap = alt.Chart(wide).mark_area(color=ORANGE, opacity=0.12).encode(
        x=x, y="Share of models:Q", y2="Share of training compute:Q")
    lines = alt.Chart(long).mark_line(strokeWidth=3).encode(x=x, y=y, color=colour)
    dots = alt.Chart(long).mark_circle(size=80, opacity=1).encode(x=x, y=y, color=colour, tooltip=tooltip)
    labels = alt.Chart(long[long["year"] == long["year"].max()]).mark_text(
        align="left", dx=10, fontSize=13, fontWeight="bold").encode(
        x=x, y=y, color=colour, text=alt.Text("share:Q", format=".0f"))
    return style_chart(gap + lines + dots + labels, height=380)


# ---------------------------------------------------------------------------
# Tab layout
# ---------------------------------------------------------------------------
def render(df, df_all):
    # df = filtered data (global filters applied), df_all = unfiltered data.
    c = models_with_compute(df)
    if len(c) < 10:
        st.warning("Too few models with reported training compute match these filters. Widen the filters above.")
        return

    st.markdown("**Is the compute behind AI concentrating, even if the number of models is not?** "
                "Counting models treats a small academic model and GPT-4 as equal. "
                "Counting training compute weighs each model by the resources it took to build.")

    # Recent era for the headline; fall back to the whole selection if it ends before 2018
    since = max(2018, int(c["year"].min())) if c["year"].max() >= 2018 else int(c["year"].min())
    comp_share, model_share, top5, n_since = overall_shares(c, 5, since)
    trends = {"pre": fit_trend(c, -np.inf, DL_START), "dl": fit_trend(c, DL_START, np.inf)}
    biggest = c.loc[c["compute_flop"].idxmax()]

    callout(f"<b>Since {since}, the top 5 organisations by compute ({', '.join(top5)}) used "
            f"<b>{comp_share:.0f}%</b> of all reported training compute but released only "
            f"<b>{model_share:.0f}%</b> of the models.</b> By compute, the frontier is far more concentrated "
            "than a model count suggests.")

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Largest training run", sci(biggest["compute_flop"]),
              f"{biggest['model']} ({biggest['org']}, {biggest['pub_date']:%Y})", delta_color="off", delta_arrow="off")
    if trends["dl"]:
        k2.metric(f"Compute doubling time since {DL_START}", f"{trends['dl']['doubling_months']:.1f} mo",
                  f"{trends['dl']['slope']:.2f} orders of magnitude per year", delta_color="off", delta_arrow="off")
    k3.metric(f"Top-5 share of compute, {since}+", f"{comp_share:.0f}%",
              f"vs {model_share:.0f}% of models", delta_color="off", delta_arrow="off")
    k4.metric("Models with reported compute", f"{len(c):,}",
              f"{len(c) / len(df) * 100:.0f}% of {len(df):,} in selection", delta_color="off", delta_arrow="off")

    # ---------- chart 1: every model on a log scale ----------
    with st.container(border=True):
        card_header("Training compute of notable AI models",
                    "Each dot is one model; the vertical axis is logarithmic, so each gridline is 10× more compute. "
                    f"Dashed lines are least-squares trends fitted before and after {DL_START}. Hover for details.")
        orgs_by_compute = (c[c["org"] != "Unknown"].groupby("org")["compute_flop"].sum()
                           .sort_values(ascending=False).index.tolist())
        highlight = st.columns([1, 3])[0].selectbox("Highlight an organisation", ["None"] + orgs_by_compute[:25],
                                 key="compute_highlight",
                                 help="Organisations are listed by total training compute in the selection.")
        highlight = None if highlight == "None" else highlight
        st.altair_chart(scatter_chart(c, trends, highlight), theme=None, width="stretch")
        pre, dl = trends["pre"], trends["dl"]
        if pre and dl:
            st.caption(f"Before {DL_START}: compute doubled every {pre['doubling_months']:.0f} months "
                       f"({pre['n']} models). From {DL_START}: every {dl['doubling_months']:.1f} months "
                       f"({dl['n']} models). Models without reported compute are not shown.")

    # ---------- chart 2: compute share vs model share ----------
    with st.container(border=True):
        card_header("Do the biggest players hold more of the compute than of the models?",
                    "Each year, organisations are ranked by total training compute. Orange = the top group's share of "
                    "that year's compute; blue = their share of that year's models. The shaded gap is the difference.")
        top_n = st.segmented_control("Top organisations per year", [1, 3, 5], default=3,
                                     format_func=lambda n: f"Top {n}", key="compute_top_n") or 3
        conc = concentration_by_year(c, top_n)
        if conc.empty:
            st.info(f"No models from {CONC_START} onwards match these filters.")
        else:
            st.altair_chart(concentration_chart(conc), theme=None, width="stretch")
            st.caption("\\* = partial year (data to the latest Epoch AI update). Only models with reported compute "
                       "and a known organisation are counted, so both lines use the same set of models. "
                       "Related names merged (Google includes DeepMind).")

    # ---------- verification helper ----------
    with st.expander("Show the data behind a number"):
        years = sorted(c["year"].unique().tolist(), reverse=True)
        year = st.selectbox("Year", years, key="compute_year")
        rows = c[c["year"] == year].sort_values("compute_flop", ascending=False)
        st.markdown(f"**{year}: {len(rows)} models with reported compute**, "
                    f"total {sci(rows['compute_flop'].sum())} FLOP")
        st.dataframe(
            rows[["model", "org", "sector", "pub_date", "compute_flop"]],
            hide_index=True,
            column_config={
                "model": "Model", "org": "Organisation", "sector": "Sector",
                "pub_date": st.column_config.DateColumn("Published", format="YYYY-MM-DD"),
                "compute_flop": st.column_config.NumberColumn("Training compute (FLOP)", format="%.2e"),
            },
        )
        st.caption("Source: Epoch AI, 'Data on AI models', column 'Training compute (FLOP)' in "
                   "data/raw/notable_ai_models.csv → compute_flop in data/processed/models_clean.csv. CC BY 4.0.")
