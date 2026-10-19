import altair as alt
import streamlit as st
from theme import BLUE, MUTED, TEXT, callout, card_header, style_chart

def render(df, df_all):
    callout("<b>Our answer (draft):</b> to be written once the group has reviewed every tab. "
            "Counting models and counting compute can point in different directions.")

    known = df[df["org"] != "Unknown"]
    counts = known["org"].value_counts()
    top5_share = counts.head(5).sum() / counts.sum() * 100

    k1, k2, k3 = st.columns(3)
    k1.metric("Notable models in selection", f"{len(df):,}")
    k2.metric("Organisations", f"{known['org'].nunique():,}")
    k3.metric("Top-5 organisations' share of models", f"{top5_share:.0f}%")

    top = counts.head(10).rename_axis("org").reset_index(name="models")
    top["share"] = top["models"] / counts.sum() * 100
    top["group"] = ["Top 5"] * 5 + ["Next 5"] * (len(top) - 5) if len(top) >= 5 else "Top 5"
    top["label"] = top.apply(lambda r: f"{r.models:,}  ·  {r.share:.0f}%", axis=1)

    with st.container(border=True):
        card_header("Which organisations release the most notable models?",
                    f"Top 10 organisations by number of notable models, {df['year'].min()}–{df['year'].max()} "
                    "(current filters). Label = models · share of models with a known organisation. "
                    "Related names merged (Google includes DeepMind). Source: Epoch AI.")
        base = alt.Chart(top).encode(
            y=alt.Y("org:N", sort=top["org"].tolist(), title=None),
            x=alt.X("models:Q", title="Notable models released (count)",
                    scale=alt.Scale(domain=[0, top["models"].max() * 1.22]),
                    axis=alt.Axis(grid=True, gridColor="#1C2840", tickCount=5)),
        )
        bars = base.mark_bar(cornerRadiusEnd=8, size=24).encode(
            color=alt.Color("group:N", title=None,
                            scale=alt.Scale(domain=["Top 5", "Next 5"], range=[BLUE, MUTED])),
            tooltip=["org", "models", alt.Tooltip("share:Q", format=".1f", title="share %")])
        labels = base.mark_text(align="left", dx=8, color=TEXT, fontSize=13, fontWeight="bold").encode(text="label:N")
        st.altair_chart(style_chart(bars + labels, height=40 * len(top) + 50), theme=None, width="stretch")