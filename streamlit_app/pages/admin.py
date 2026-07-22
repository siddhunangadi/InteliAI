import json

import api_client
import streamlit as st

st.title("Admin diagnostics")

resp = api_client.get("/diagnostics")
if not resp.ok:
    st.error(f"/diagnostics failed: {resp.status_code} {resp.text}")
    st.stop()

body = resp.json()

col1, col2, col3 = st.columns(3)
col1.metric("Build", f"{body['build']['name']} {body['build']['version']}")
col2.metric("Documents", body["ingestion_stats"]["total_documents"])
col3.metric("Chunks", body["ingestion_stats"]["total_chunks"])

st.subheader("Providers")
st.json(body["providers"])

st.subheader("Metrics")
metrics = body["metrics"]
mcol1, mcol2 = st.columns(2)
mcol1.metric("Avg latency (ms)", f"{metrics['avg_latency_ms']:.1f}")
mcol2.metric("Total requests", metrics["request_count"])
st.json(metrics["counts"])

st.subheader("Readiness")
for check in body["readiness"]:
    icon = "✅" if check["ok"] else "❌"
    st.write(f"{icon} {check['name']}" + (f" — {check['detail']}" if check.get("detail") else ""))

st.subheader("Config (secrets scrubbed)")
st.code(json.dumps(body["config"], indent=2, default=str), language="json")

st.subheader("Audit stats")
st.json(body["audit_stats"])
