import streamlit as st
from common import load_data, SOURCE_LINE
from theme import apply_theme, hero
from tabs import overview, organisations, compute, geography, methods

st.set_page_config(page_title="Who controls the AI frontier?", layout="wide")
apply_theme()

df_all = load_data()

# ---------- header ----------
hero("Data Narrative Studio · Artificial Intelligence",
     "Who Controls the AI Frontier?",
     "Is frontier AI development concentrating in fewer organisations, or spreading out?",
     "Notable = models in Epoch AI's notable-models list. Frontier = the subset Epoch flags as frontier "
     "(tick the box below). The default view shows all notable models.")

# ---------- shared filters ----------
c1, c2, c3 = st.columns([2, 2, 1])
y_min, y_max = int(df_all["year"].min()), int(df_all["year"].max())
years = c1.slider("Publication year", y_min, y_max, (y_min, y_max))          # default = whole dataset
sectors = c2.multiselect("Sector", sorted(df_all["sector"].unique()), default=sorted(df_all["sector"].unique()))
frontier_only = c3.checkbox("Frontier models only (Epoch flag)", value=False)

df = df_all[df_all["year"].between(*years) & df_all["sector"].isin(sectors)]
if frontier_only:
    df = df[df["frontier"]]

# ---------- empty state ----------
if df.empty:
    st.info("No models match these filters. Widen the year range, select at least one sector, "
            "or untick 'Frontier models only'.")
    st.stop()

# ---------- tabs ----------
t1, t2, t3, t4, t5 = st.tabs(["Overview", "Organisations", "Compute", "Geography", "Data & methods"])
with t1: overview.render(df, df_all)
with t2: organisations.render(df, df_all)
with t3: compute.render(df, df_all)
with t4: geography.render(df, df_all)
with t5: methods.render(df, df_all)

st.divider()
st.caption(SOURCE_LINE)