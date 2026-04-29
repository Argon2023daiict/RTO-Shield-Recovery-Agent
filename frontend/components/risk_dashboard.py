"""
Risk Dashboard Component - Displays risk assessment metrics and high-risk orders.
"""

import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

BACKEND_URL = "http://localhost:8000"


def render_risk_dashboard():
    st.subheader("🛡️ Risk Assessment Overview")

    # Fetch analytics
    try:
        resp = requests.get(f"{BACKEND_URL}/api/dashboard/analytics/summary", timeout=10)
        analytics = resp.json()
    except Exception as e:
        st.error(f"Cannot reach backend: {e}")
        return

    risk_dist = analytics.get("risk_distribution", {})
    shield = analytics.get("shield_performance", {})

    # KPI cards
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🔍 Orders Assessed", shield.get("orders_assessed", 0))
    with col2:
        st.metric("🚫 Orders Blocked", shield.get("orders_blocked", 0))
    with col3:
        st.metric("💰 Est. Savings (₹)", f"₹{shield.get('estimated_savings', 0):,.0f}")
    with col4:
        total_risk = sum(risk_dist.values()) or 1
        high_pct = round(
            ((risk_dist.get("high", 0) + risk_dist.get("critical", 0)) / total_risk) * 100, 1
        )
        st.metric("⚠️ High/Critical Rate", f"{high_pct}%")

    st.divider()

    col_left, col_right = st.columns(2)

    with col_left:
        # Risk distribution donut chart
        if risk_dist:
            labels = list(risk_dist.keys())
            values = list(risk_dist.values())
            colors = {"low": "#27ae60", "medium": "#f39c12", "high": "#e74c3c", "critical": "#8e44ad"}
            fig = go.Figure(go.Pie(
                labels=labels, values=values,
                hole=0.5,
                marker_colors=[colors.get(l, "#95a5a6") for l in labels],
            ))
            fig.update_layout(title="Risk Distribution", height=300, margin=dict(t=40, b=0))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No risk data yet. Run Shield Agent on some orders.")

    with col_right:
        # High risk orders table
        try:
            hr_resp = requests.get(f"{BACKEND_URL}/api/dashboard/analytics/high-risk-orders?limit=10", timeout=10)
            high_risk = hr_resp.json()
        except Exception:
            high_risk = []

        if high_risk:
            st.markdown("**🔴 Top High-Risk Orders**")
            df = pd.DataFrame(high_risk)[["order_number", "customer_name", "amount", "risk_score", "risk_level", "status"]]
            df.columns = ["Order", "Customer", "Amount (₹)", "Risk Score", "Level", "Status"]
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No high-risk orders found.")
