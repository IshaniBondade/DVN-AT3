import altair as alt
import streamlit as st
from theme import BLUE, MUTED, TEXT, callout, card_header, style_chart

def render(df, df_all):
    known = df[df["org"] != "Unknown"]
    n_unknown = len(df) - len(known)
    # ties are broken alphabetically so the Top 5 / Next 5 split is stable and explainable
    counts = (known.groupby("org").size().rename("n").reset_index()
              .sort_values(["n", "org"], ascending=[False, True]).set_index("org")["n"])
    top5_share = counts.head(5).sum() / counts.sum() * 100
    leader, leader_share = counts.index[0], counts.iloc[0] / counts.sum() * 100
    y0, y1 = int(df["year"].min()), int(df["year"].max())

    # data-driven summary: every number comes from the current selection
    period = f"{y0}" if y0 == y1 else f"{y0}–{y1}"
    n_orgs = len(counts)
    if n_orgs == 1:
        summary = f"in {period}, the only organisation listed was {leader}."
    else:
        who = "the top 5 organisations" if n_orgs > 5 else f"all {n_orgs} organisations in this selection"
        summary = (f"in {period}, {who} released <b>{top5_share:.0f}%</b> of notable models, and the largest, "
                   f"{leader}, released <b>{leader_share:.0f}%</b>.")
    small = (f" With only {len(known)} models in this selection, shares can swing sharply."
             if len(known) < 30 else "")
    callout(f"<b>What this view shows:</b> {summary}{small} Whether the top-5 share is rising or falling "
            "over time is shown on the Organisations tab.")

    k1, k2, k3 = st.columns(3)
    k1.metric("Notable models in selection", f"{len(df):,}")
    k2.metric("Organisations", f"{known['org'].nunique():,}")
    k3.metric("Top-5 organisations' share of models", f"{top5_share:.0f}%")

    top = counts.head(10).rename_axis("org").reset_index(name="models")
    top["share"] = top["models"] / counts.sum() * 100
    top["org_label"] = top["org"].map(lambda n: n.split(" / ")[0])      # drop bilingual duplicates
    top["group"] = ["Top 5" if i < 5 else "Next 5" for i in range(len(top))]
    top["label"] = top.apply(lambda r: f"{r.models:,}  ·  {r.share:.0f}%", axis=1)

    partial = " The latest year (2026) is partial: data runs to 30 Sep." if (df["partial_year"].any()) else ""
    with st.container(border=True):
        card_header("Which organisations release the most notable models?",
                    f"Top 10 organisations by number of notable models, {y0}–{y1} (current filters).{partial} "
                    f"Label = models · share of the {len(known):,} models with a known organisation "
                    f"({n_unknown} with no organisation listed are excluded). Models with several organisations "
                    "are credited to the first one listed. Related names are merged (Google includes DeepMind). "
                    "Ties in the ranking are ordered alphabetically. Source: Epoch AI.")
        base = alt.Chart(top).encode(
            y=alt.Y("org_label:N", sort=top["org_label"].tolist(), title="Organisation",
                    axis=alt.Axis(titleAngle=0, titleAlign="left", titleAnchor="start", titleY=-14,
                                  labelLimit=420, labelPadding=8)),
            x=alt.X("models:Q", title="Notable models released (count)",
                    scale=alt.Scale(domain=[0, top["models"].max() * 1.22]),
                    axis=alt.Axis(grid=True, gridColor="#1C2840", tickCount=5, format="d",
                                  domain=True, domainColor="#5B6F94", domainWidth=1.5,
                                  ticks=True, tickColor="#5B6F94", tickSize=7, tickWidth=1.5,
                                  labelPadding=8, titlePadding=18,
                                  values=list(range(int(top["models"].max()) + 1)) if top["models"].max() <= 8 else alt.Undefined)),
        )
        bars = base.mark_bar(cornerRadiusEnd=8, size=24).encode(
            color=alt.Color("group:N", title="Rank group (by model count)",
                            scale=alt.Scale(domain=["Top 5", "Next 5"], range=[BLUE, MUTED])),
            tooltip=[alt.Tooltip("org:N", title="organisation"), "models", alt.Tooltip("share:Q", format=".1f", title="share %")])
        labels = base.mark_text(align="left", dx=8, color=TEXT, fontSize=13, fontWeight="bold").encode(text="label:N")
        st.altair_chart(style_chart(bars + labels, height=max(40 * len(top) + 50, 230)), theme=None, width="stretch")