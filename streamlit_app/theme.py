"""Warm nude/paper/clay theme from DESIGN.md, applied via CSS injection.

Streamlit has no theme API for per-widget borders/radii, so the palette is
applied with a CSS override block rather than reimplementing components.
"""

import streamlit as st

CSS = """
<style>
:root {
    --sand: #f1e9e2;
    --paper: #faf6f2;
    --paper-raised: #e9ded3;
    --rule: #d9c9b8;
    --ink: #2b2118;
    --ink-muted: #6b5d52;
    --clay: #a9613f;
    --clay-hover: #8f4e32;
    --moss: #4f7a4a;
    --ochre: #9c6b1f;
    --brick: #a4402f;
}
html, body, [class*="css"] { font-family: Inter, -apple-system, sans-serif; }
.stApp { background-color: var(--sand); color: var(--ink); }
section[data-testid="stSidebar"] { background-color: var(--sand); border-right: 1px solid var(--rule); }
h1, h2, h3 { font-family: "Inter Tight", Inter, sans-serif; letter-spacing: -0.02em; color: var(--ink); }
div[data-testid="stMetric"], .stAlert, div[data-testid="stExpander"], div[data-testid="stForm"] {
    background-color: var(--paper);
    border: 1px solid var(--rule);
    border-radius: 10px;
}
.stButton > button[kind="primary"] {
    background-color: var(--clay);
    color: var(--paper);
    border-radius: 6px;
    border: none;
}
.stButton > button[kind="primary"]:hover { background-color: var(--clay-hover); }
.stButton > button:not([kind="primary"]) {
    background-color: var(--paper-raised);
    color: var(--ink);
    border: 1px solid var(--rule);
    border-radius: 6px;
}
code, pre, .stCodeBlock, .stCode { font-family: "IBM Plex Mono", ui-monospace, monospace !important; }
</style>
"""


def apply() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
