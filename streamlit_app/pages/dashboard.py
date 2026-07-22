import api_client
import streamlit as st

st.title("Dashboard")

col1, col2, col3 = st.columns(3)

health = api_client.get("/health")
docs = api_client.get("/documents")
ready = api_client.get("/health/ready")

if health.ok:
    body = health.json()
    col1.metric("Status", body["status"])
    col1.caption(f"gen: {body['generation_provider']} · embed: {body['embedding_provider']}")
else:
    col1.error(f"/health failed: {health.status_code}")

if docs.ok:
    body = docs.json()
    col2.metric("Documents indexed", body["total_documents"])
    col3.metric("Chunks indexed", body["total_chunks"])
else:
    col2.error(f"/documents failed: {docs.status_code}")

st.subheader("Readiness")
if ready.ok:
    body = ready.json()
    st.write(f"Overall: **{body['status']}**")
    for check in body["checks"]:
        icon = "✅" if check["ok"] else "❌"
        st.write(f"{icon} {check['name']}" + (f" — {check['detail']}" if check.get("detail") else ""))
else:
    st.error(f"/health/ready failed: {ready.status_code}")
