import api_client
import streamlit as st

st.title("Upload documents")

DOCUMENT_TYPES = ["general", "regulation", "policy", "contract", "standard", "guideline"]
RISK_CATEGORIES = ["", "low", "medium", "high", "critical"]

with st.form("upload_form", clear_on_submit=False):
    files = st.file_uploader(
        "Files", accept_multiple_files=True,
        type=["md", "markdown", "html", "htm", "txt", "pdf", "csv", "xlsx", "docx"],
    )
    document_type = st.selectbox("Document type", DOCUMENT_TYPES)
    col1, col2 = st.columns(2)
    regulation = col1.text_input("Regulation (compliance docs only)")
    authority = col2.text_input("Authority")
    jurisdiction = col1.text_input("Jurisdiction")
    effective_date = col2.date_input("Effective date", value=None)
    risk_category = st.selectbox("Risk category", RISK_CATEGORIES)
    submitted = st.form_submit_button("Upload", type="primary")

if submitted:
    if not files:
        st.warning("Choose at least one file.")
    else:
        data = {"document_type": document_type}
        if regulation:
            data["regulation"] = regulation
        if authority:
            data["authority"] = authority
        if jurisdiction:
            data["jurisdiction"] = jurisdiction
        if effective_date:
            data["effective_date"] = effective_date.isoformat()
        if risk_category:
            data["risk_category"] = risk_category

        upload_files = [("files", (f.name, f.getvalue())) for f in files]
        with st.spinner("Ingesting..."):
            resp = api_client.post("/upload", files=upload_files, data=data)

        if resp.ok:
            for result in resp.json()["results"]:
                if result["status"] == "ready":
                    st.success(f"{result['filename']}: ready")
                else:
                    st.error(f"{result['filename']}: {result.get('error', 'failed')}")
        else:
            st.error(f"Upload failed: {resp.status_code} {resp.text}")
