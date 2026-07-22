import json

import api_client
import streamlit as st

st.title("Audit log")

with st.sidebar:
    event_type = st.text_input("Event type filter")
    status = st.selectbox("Status", ["", "success", "failure"])
    document_id = st.text_input("Document ID filter")
    limit = st.slider("Limit", 10, 500, 50)

params = {"limit": limit, "sort": "desc"}
if event_type:
    params["event_type"] = event_type
if status:
    params["status"] = status
if document_id:
    params["document_id"] = document_id

resp = api_client.get("/audit/events", params=params)
if not resp.ok:
    st.error(f"/audit/events failed: {resp.status_code}")
    st.stop()

body = resp.json()
st.caption(f"{body['total']} total events, showing {len(body['events'])}")

for event in body["events"]:
    icon = "✅" if event["status"] == "success" else "❌"
    st.write(f"{icon} `{event['timestamp']}` **{event['action']}** ({event['event_type']}) — {event['endpoint']}")
    with st.expander("details"):
        st.code(json.dumps(event, indent=2, default=str), language="json")
