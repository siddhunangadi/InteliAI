import api_client
import streamlit as st

st.title("System status")

live = api_client.get("/health/live")
ready = api_client.get("/health/ready")
version = api_client.get("/version")

col1, col2, col3 = st.columns(3)
col1.metric("Liveness", live.json()["status"] if live.ok else "unreachable")
col2.metric("Readiness", ready.json()["status"] if ready.ok else "unreachable")
if version.ok:
    v = version.json()
    col3.metric("Version", f"{v['name']} {v['version']}")

if ready.ok:
    st.subheader("Dependency checks")
    for check in ready.json()["checks"]:
        icon = "✅" if check["ok"] else "❌"
        st.write(f"{icon} {check['name']}" + (f" — {check['detail']}" if check.get("detail") else ""))
