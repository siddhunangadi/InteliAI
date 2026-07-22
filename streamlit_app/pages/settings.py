import api_client
import streamlit as st

st.title("Settings")

st.session_state.setdefault("api_base_url", api_client.DEFAULT_BASE_URL)
st.session_state.setdefault("api_key", "")

st.session_state["api_base_url"] = st.text_input("API base URL", value=st.session_state["api_base_url"])
st.session_state["api_key"] = st.text_input("X-API-Key", value=st.session_state["api_key"], type="password")

if st.button("Test connection", type="primary"):
    resp = api_client.get("/health")
    if resp.ok:
        st.success(f"Connected: {resp.json()}")
    else:
        st.error(f"Failed: {resp.status_code} {resp.text}")
