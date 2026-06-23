import streamlit as st

from core.assistant import interactive_handle

st.set_page_config(page_title="Pokedex Assistant", page_icon="P", layout="centered")

st.title("Pokedex Assistant")
st.caption("Ask Pokemon questions in plain English.")

if "last_context" not in st.session_state:
    st.session_state.last_context = None

if "history" not in st.session_state:
    st.session_state.history = []

with st.form("query_form", clear_on_submit=True):
    query = st.text_input(
        "Question",
        placeholder="Example: what abilities does garchomp have",
    )
    submitted = st.form_submit_button("Ask")

if submitted:
    user_query = (query or "").strip()
    if user_query:
        response, context = interactive_handle(user_query, st.session_state.last_context)
        st.session_state.last_context = context
        st.session_state.history.append((user_query, response))

if st.session_state.history:
    st.divider()
    for idx, (q, a) in enumerate(reversed(st.session_state.history), start=1):
        st.markdown(f"Question {len(st.session_state.history) - idx + 1}: {q}")
        st.text(a)
