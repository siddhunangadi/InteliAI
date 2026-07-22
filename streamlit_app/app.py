"""InteliAI Streamlit entrypoint: navigation shell for all pages.

Run with: uv run streamlit run streamlit_app/app.py
"""

import streamlit as st

import theme

st.set_page_config(page_title="InteliAI", page_icon="\U0001f4c4", layout="wide")
theme.apply()

pages = [
    st.Page("pages/dashboard.py", title="Dashboard", icon="\U0001f4ca"),
    st.Page("pages/upload.py", title="Upload", icon="\U0001f4e4"),
    st.Page("pages/chat.py", title="Chat", icon="\U0001f4ac"),
    st.Page("pages/regulations.py", title="Regulations", icon="\U0001f4d1"),
    st.Page("pages/audit.py", title="Audit", icon="\U0001f9fe"),
    st.Page("pages/health.py", title="Status", icon="\U0001f49a"),
    st.Page("pages/admin.py", title="Admin", icon="\U0001f6e0️"),
    st.Page("pages/settings.py", title="Settings", icon="⚙️"),
]

nav = st.navigation(pages)
nav.run()
