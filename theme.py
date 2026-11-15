"""Look and feel for the whole app. Everyone reuses apply_theme(), style_chart() and the colours."""
import altair as alt
import streamlit as st

# Colour-blind-safe pair (blue vs orange) plus muted greys; never rely on colour alone (use labels).
BLUE = "#4C8DFF"      # main accent
ORANGE = "#FFB000"    # highlight / call-out
TEAL = "#2EC4B6"
MUTED = "#4A5C80"     # de-emphasised bars
TEXT = "#E8EEF9"
SUBTLE = "#8FA0BF"
CARD = "#101828"
BORDER = "#24324D"

CSS = f"""
<style>
.block-container {{ padding-top: 1.6rem; max-width: 1400px; }}
header[data-testid="stHeader"] {{ background: transparent; }}

.hero {{ background: linear-gradient(135deg,#17386B 0%,#0F2040 55%,#0B1530 100%);
        border: 1px solid #2B4A80; border-radius: 22px; padding: 28px 34px; margin-bottom: 22px; }}
.hero .eyebrow {{ letter-spacing: .16em; font-size: .72rem; color: #8FB3F5; text-transform: uppercase; }}
.hero h1 {{ font-size: 2.5rem; font-weight: 800; color: #fff; margin: .35rem 0 .25rem 0; padding: 0; }}
.hero .q {{ font-size: 1.22rem; color: #CFE0FF; margin: 0; }}
.hero .sub {{ font-size: .95rem; color: {SUBTLE}; margin-top: .55rem; }}

/* tabs as pills (role-based selectors work across Streamlit versions) */
[role="tablist"] {{ gap: 10px; border-bottom: none !important; box-shadow: none !important;
                    padding-bottom: 6px; margin-bottom: 10px; }}
[role="tablist"]::after {{ display: none !important; }}
[role="tab"] {{ border: 1px solid #2A3A58 !important; border-radius: 999px !important; padding: 8px 22px !important;
                background: #0F1626 !important; height: auto !important; }}
[role="tab"][aria-selected="true"] {{ background: {TEXT} !important; border-color: {TEXT} !important; }}
[role="tab"][aria-selected="true"] p {{ color: #0A0F1A !important; font-weight: 700; }}
.react-aria-SelectionIndicator, div[data-baseweb="tab-highlight"], div[data-baseweb="tab-border"] {{ display: none !important; }}

/* KPI cards */
div[data-testid="stMetric"] {{ background: #131C2E; border: 1px solid {BORDER}; border-radius: 16px;
                               padding: 18px 22px; }}
div[data-testid="stMetricValue"] {{ font-size: 2.5rem; font-weight: 800; }}
div[data-testid="stMetricLabel"] p {{ color: {SUBTLE}; font-size: .9rem; }}

/* bordered containers = chart cards */
div[data-testid="stVerticalBlockBorderWrapper"] {{ background: {CARD}; border: 1px solid {BORDER};
                                                    border-radius: 18px; }}
.callout {{ background: #1A1608; border-left: 4px solid {ORANGE}; border-radius: 10px;
           padding: 14px 18px; color: #F5E6BF; margin: 6px 0 18px 0; }}
.card-title {{ font-size: 1.25rem; font-weight: 700; margin: 0 0 2px 0; }}
.card-sub {{ color: {SUBTLE}; font-size: .9rem; margin-bottom: 8px; }}
</style>
"""

def apply_theme():
    st.markdown(CSS, unsafe_allow_html=True)

def hero(eyebrow, title, question, sub=""):
    st.markdown(
        f'<div class="hero"><div class="eyebrow">{eyebrow}</div><h1>{title}</h1>'
        f'<p class="q">{question}</p><div class="sub">{sub}</div></div>',
        unsafe_allow_html=True)

def callout(html):
    st.markdown(f'<div class="callout">{html}</div>', unsafe_allow_html=True)

def card_header(title, sub=""):
    st.markdown(f'<div class="card-title">{title}</div><div class="card-sub">{sub}</div>',
                unsafe_allow_html=True)

def style_chart(chart, height=380):
    """Dark, clean Altair styling. Use: st.altair_chart(style_chart(ch), theme=None, width='stretch')."""
    return (chart.properties(height=height, background="transparent")
            .configure_view(stroke=None)
            .configure_axis(labelColor="#C9D8F5", titleColor=SUBTLE, labelFontSize=13, titleFontSize=13, titleFontWeight="normal",
                            domain=False, ticks=False, grid=False, labelLimit=280)
            .configure_legend(labelColor="#C9D8F5", titleColor=SUBTLE, labelFontSize=12, orient="top"))