"""
Agent Chat Component - Natural language query interface for the merchant dashboard.
"""

import streamlit as st
import requests

BACKEND_URL = "http://localhost:8000"

SUGGESTED_QUESTIONS = [
    "What are my top 5 high-risk COD orders?",
    "How much have I lost to RTO this month?",
    "Which customers have the highest return rates?",
    "Show me recovery success rate",
    "How many orders are pending assessment?",
    "What is my RTO rate for COD orders?",
]


def render_agent_chat():
    st.subheader("🤖 Ask the AI Agent")
    st.caption("Ask anything about your orders, risk, or recovery performance in plain English.")

    # Initialize chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Suggested questions
    with st.expander("💡 Suggested Questions", expanded=False):
        for q in SUGGESTED_QUESTIONS:
            if st.button(q, key=f"suggested_{q[:20]}"):
                st.session_state.pending_query = q

    # Display chat history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    user_input = st.chat_input("Ask about your orders...")
    if "pending_query" in st.session_state:
        user_input = st.session_state.pop("pending_query")

    if user_input:
        # Show user message
        with st.chat_message("user"):
            st.markdown(user_input)
        st.session_state.chat_history.append({"role": "user", "content": user_input})

        # Get response
        with st.chat_message("assistant"):
            with st.spinner("Analyzing your data..."):
                try:
                    resp = requests.post(
                        f"{BACKEND_URL}/api/dashboard/chat",
                        json={"message": user_input},
                        timeout=60,
                    )
                    result = resp.json()
                    response_text = result.get("response", "Sorry, I couldn't process that.")
                except Exception as e:
                    response_text = f"⚠️ Error: {str(e)}. Make sure the backend is running."

            st.markdown(response_text)
            st.session_state.chat_history.append({"role": "assistant", "content": response_text})

    # Clear chat button
    if st.session_state.chat_history:
        if st.button("🗑️ Clear Chat"):
            st.session_state.chat_history = []
            st.rerun()
