"""
Analytics Component - Charts and financial impact visualizations.
"""

import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

BACKEND_URL = "http://localhost:8000"


def render_analytics():
    st.subheader("📊 Analytics & Financial Impact")

    try:
        resp = requests.get(f"{BACKEND_URL}/api/dashboard/analytics/summary", timeout=10)
        data = resp.json()
    except Exception as e:
        st.error(f"Cannot reach backend: {e}")
        return

    orders = data.get("orders", {})
    rto = data.get("rto", {})
    recovery = data.get("recovery", {})
    agent_activity = data.get("agent_activity", {})

    # Top KPIs
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📦 Total Orders", orders.get("total", 0))
        st.metric("💵 COD Orders", orders.get("cod", 0))
    with col2:
        st.metric("↩️ RTO Orders", rto.get("total_rto_orders", 0))
        st.metric("📉 RTO Rate", f"{rto.get('rto_rate', 0)}%")
    with col3:
        st.metric("💸 Shipping Lost (₹)", f"₹{rto.get('total_shipping_lost', 0):,.0f}")
        st.metric("⚠️ Revenue at Risk (₹)", f"₹{rto.get('total_revenue_at_risk', 0):,.0f}")
    with col4:
        st.metric("🔄 Recovery Attempted", recovery.get("attempted", 0))
        st.metric("✅ Recovery Rate", f"{recovery.get('success_rate', 0)}%")

    st.divider()

    col_left, col_right = st.columns(2)

    with col_left:
        # Order status breakdown
        status_dist = data.get("status_distribution", {})
        if status_dist:
            fig = px.bar(
                x=list(status_dist.keys()),
                y=list(status_dist.values()),
                title="Orders by Status",
                labels={"x": "Status", "y": "Count"},
                color=list(status_dist.values()),
                color_continuous_scale="RdYlGn_r",
            )
            fig.update_layout(height=300, margin=dict(t=40, b=0), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    with col_right:
        # Agent activity
        agent_data = {
            "Agent": ["🛡️ Shield Agent", "🔄 Recovery Agent"],
            "Actions": [
                agent_activity.get("shield_agent_actions", 0),
                agent_activity.get("recovery_agent_actions", 0),
            ],
        }
        fig2 = px.pie(
            names=agent_data["Agent"],
            values=agent_data["Actions"],
            title="Agent Activity Split",
            color_discrete_sequence=["#3498db", "#2ecc71"],
        )
        fig2.update_layout(height=300, margin=dict(t=40, b=0))
        st.plotly_chart(fig2, use_container_width=True)

    # RTO Timeline
    st.subheader("📅 RTO Timeline (Last 30 Days)")
    try:
        tl_resp = requests.get(f"{BACKEND_URL}/api/dashboard/analytics/rto-timeline?days=30", timeout=10)
        timeline = tl_resp.json()
        if timeline:
            df = pd.DataFrame(timeline)
            df["created_at"] = pd.to_datetime(df["created_at"])
            fig3 = px.scatter(
                df, x="created_at", y="amount", color="status",
                size="rto_cost", hover_data=["order_number", "rto_cost"],
                title="RTO Events Over Time",
                labels={"created_at": "Date", "amount": "Order Amount (₹)"},
            )
            fig3.update_layout(height=350)
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("No RTO events in the last 30 days.")
    except Exception:
        st.info("Timeline data unavailable.")
