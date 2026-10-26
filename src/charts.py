"""Plotly figures built from prepared data; no file or network I/O."""
from __future__ import annotations

import html

import pandas as pd
import plotly.graph_objects as go

PALETTE = ["#7AAFFF", "#51D3B6", "#F1C074", "#D0A9FC"]
OTHER = "#657990"
TEXT = "#EAF1FC"
MUTED = "#B4C5DD"


def _theme(fig: go.Figure, height: int) -> go.Figure:
    fig.update_layout(template="plotly_dark", height=height, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(family="Arial, sans-serif", color=TEXT, size=12), margin=dict(l=10, r=10, t=15, b=10), hoverlabel=dict(bgcolor="#FFFFFF", font_color="#172C44", font_size=12))
    return fig


def trend_chart(table: pd.DataFrame, selected: list[str], periods: list, active_period: int) -> go.Figure:
    fig = go.Figure()
    labels = [f"{start}–{end}" for start, end in periods]
    for i, country in enumerate([*selected, "Other origins"]):
        rows = table.loc[table["country"].eq(country)].set_index("period").reindex(labels)
        shares = rows["share"].fillna(0).tolist()
        legend_name = {"United States": "US", "United Kingdom": "UK", "United Arab Emirates": "UAE"}.get(country, country)
        fig.add_trace(go.Bar(name=legend_name, x=labels, y=[v * 100 for v in shares], marker=dict(color=OTHER if country == "Other origins" else PALETTE[i % len(PALETTE)], line_width=0), customdata=[[j, country] for j in range(len(labels))], text=[f"{v:.0%}" if v > .14 else "" for v in shares], textposition="inside", insidetextanchor="middle", hovertemplate="%{customdata[1]}<br>%{x}: %{y:.1f}%<extra></extra>"))
    _theme(fig, 330)
    fig.update_layout(barmode="stack", bargap=.32, clickmode="event+select", dragmode=False, legend=dict(orientation="h", traceorder="normal", y=1.16, x=0, font_size=11), margin=dict(l=55, r=12, t=65, b=45), uniformtext=dict(minsize=11, mode="hide"))
    fig.update_xaxes(title="Publication period", tickfont_size=11, fixedrange=True)
    fig.update_yaxes(title="Global model share (%)", range=[0, 100], ticksuffix="%", gridcolor="#30445F", fixedrange=True)
    # Keep highlighting on the background. Per-point marker.opacity arrays
    # suppressed native selection events in the tested Plotly/Streamlit stack.
    fig.add_vrect(x0=active_period-.46, x1=active_period+.46, fillcolor="#6B91C8", opacity=.17, line_width=0, layer="below")
    return fig


def type_distribution(table: pd.DataFrame, domain: str) -> go.Figure:
    labels = table["country"].tolist()
    values = (table["share"] * 100).tolist()
    fig = go.Figure(go.Bar(x=values, y=labels, orientation="h", marker=dict(color=[OTHER if c == "Other origins" else "#8DBBFA" for c in labels], line_width=0), customdata=[[c, domain] for c in labels], text=[f"{v:.1f}%" for v in values], textposition="outside", cliponaxis=False, hovertemplate="%{y}<br>%{x:.2f}% of global " + html.escape(domain) + " model credit<extra></extra>"))
    _theme(fig, max(235, 34 * len(labels) + 65))
    fig.update_layout(clickmode="event+select", dragmode=False, margin=dict(l=0, r=45, t=5, b=45), showlegend=False)
    fig.update_yaxes(autorange="reversed", automargin=True, fixedrange=True)
    fig.update_xaxes(title="Share of this AI type globally (%)", range=[0, 100], ticksuffix="%", gridcolor="#30445F", fixedrange=True)
    return fig
