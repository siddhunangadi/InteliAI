import api_client
import streamlit as st

st.title("Regulations")

resp = api_client.get("/documents")
if not resp.ok:
    st.error(f"/documents failed: {resp.status_code}")
    st.stop()

documents = resp.json()["documents"]
if not documents:
    st.info("No documents indexed yet. Upload some on the Upload page.")
    st.stop()

for doc in documents:
    with st.expander(f"{doc['filename']} — {doc['chunk_count']} chunks"):
        st.caption(f"document_id: {doc['document_id']}" + (f" · indexed: {doc['indexed_at']}" if doc.get("indexed_at") else ""))
        col1, col2 = st.columns([1, 1])
        if col1.button("Load detail", key=f"detail_{doc['document_id']}"):
            detail_resp = api_client.get(f"/documents/{doc['document_id']}")
            if detail_resp.ok:
                detail = detail_resp.json()
                meta = " · ".join(
                    f"{k}: {v}" for k, v in
                    [("regulation", detail.get("regulation")), ("authority", detail.get("authority")),
                     ("jurisdiction", detail.get("jurisdiction")), ("article", detail.get("article")),
                     ("section", detail.get("section")), ("clause", detail.get("clause")),
                     ("effective_date", detail.get("effective_date")), ("risk_category", detail.get("risk_category"))]
                    if v
                )
                if meta:
                    st.caption(meta)
                st.code(detail["content_preview"], language=None)
            else:
                st.error(f"Detail failed: {detail_resp.status_code}")
        if col2.button("Delete", key=f"delete_{doc['document_id']}", type="primary"):
            delete_resp = api_client.delete(f"/documents/{doc['document_id']}")
            if delete_resp.ok:
                st.success(f"Deleted, {delete_resp.json()['chunks_deleted']} chunks removed.")
                st.rerun()
            else:
                st.error(f"Delete failed: {delete_resp.status_code}")
