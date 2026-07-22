import api_client
import streamlit as st

st.title("Chat")

if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    max_chunks = st.slider("Max chunks", 1, 20, 5)
    verify = st.checkbox("Verify citations", value=True)

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if msg["role"] == "assistant":
            answer = msg["answer"]
            conf = answer["confidence"]["overall"]
            st.caption(f"confidence: {conf:.0%} · status: {answer['citation_status']}")
            for c in answer["structured_citations"]:
                with st.expander(f"📎 {c['display']}"):
                    meta = " · ".join(
                        f"{k}: {v}" for k, v in
                        [("regulation", c.get("regulation")), ("section", c.get("section")),
                         ("clause", c.get("clause")), ("page", c.get("page"))]
                        if v
                    )
                    if meta:
                        st.caption(meta)
                    st.code(c.get("chunk_text", ""), language=None)

if question := st.chat_input("Ask a question..."):
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.write(question)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            resp = api_client.post(
                "/answer",
                json={"question": question, "max_chunks": max_chunks, "verify": verify},
            )
        if resp.ok:
            answer = resp.json()
            st.write(answer["answer"] or "_(no answer)_")
            conf = answer["confidence"]["overall"]
            st.caption(f"confidence: {conf:.0%} · status: {answer['citation_status']}")
            for c in answer["structured_citations"]:
                with st.expander(f"📎 {c['display']}"):
                    meta = " · ".join(
                        f"{k}: {v}" for k, v in
                        [("regulation", c.get("regulation")), ("section", c.get("section")),
                         ("clause", c.get("clause")), ("page", c.get("page"))]
                        if v
                    )
                    if meta:
                        st.caption(meta)
                    st.code(c.get("chunk_text", ""), language=None)
            st.session_state.messages.append(
                {"role": "assistant", "content": answer["answer"] or "", "answer": answer}
            )
        else:
            st.error(f"Request failed: {resp.status_code} {resp.text}")
