"""
Order Tracker Component - Browse, filter, and act on orders.
"""

import streamlit as st
import requests
import pandas as pd

BACKEND_URL = "http://localhost:8000"


def api(endpoint, method="GET", data=None):
    url = f"{BACKEND_URL}{endpoint}"
    try:
        if method == "GET":
            r = requests.get(url, timeout=30)
        else:
            r = requests.post(url, json=data, timeout=120)
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def render_order_tracker():
    st.subheader("📦 Order Tracker")

    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        status_filter = st.selectbox("Filter by Status", [
            "all", "pending", "approved", "flagged", "cancelled",
            "dispatched", "delivered", "rto_received", "recovery_initiated"
        ])
    with col2:
        risk_filter = st.selectbox("Filter by Risk", ["all", "low", "medium", "high", "critical"])
    with col3:
        limit = st.slider("Max Results", 10, 100, 25)

    params = f"?limit={limit}"
    if status_filter != "all":
        params += f"&status={status_filter}"
    if risk_filter != "all":
        params += f"&risk_level={risk_filter}"

    orders = api(f"/api/orders/{params}")

    if isinstance(orders, dict) and "error" in orders:
        st.error(orders["error"])
        return

    if not orders:
        st.info("No orders match your filters.")
        return

    # Build display dataframe
    rows = []
    for o in orders:
        rows.append({
            "Order #": o.get("order_number", ""),
            "Customer": o.get("customer_name", ""),
            "Amount (₹)": f"₹{o.get('total_amount', 0):,.0f}",
            "Method": o.get("payment_method", "").upper(),
            "Status": o.get("status", ""),
            "Risk Score": o.get("risk_score") or "-",
            "Risk Level": (o.get("risk_level") or "").upper(),
            "Created": o.get("created_at", "")[:10] if o.get("created_at") else "",
            "_id": o.get("id", ""),
        })

    df = pd.DataFrame(rows)
    display_df = df.drop(columns=["_id"])
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # Quick actions
    st.divider()
    st.markdown("**⚡ Quick Actions**")
    col_a, col_b, col_c = st.columns(3)

    order_ids = [f"{r['Order #']} ({r['_id'][:8]}...)" for r in rows]
    selected = st.selectbox("Select Order", order_ids) if rows else None

    if selected:
        selected_id = rows[order_ids.index(selected)]["_id"]

        with col_a:
            if st.button("🛡️ Run Shield Agent"):
                with st.spinner("Assessing risk..."):
                    result = api(f"/api/agents/assess/{selected_id}", method="POST")
                if result.get("success"):
                    st.success(f"Risk: {result.get('risk_level')} (Score: {result.get('risk_score')})")
                    st.json(result)
                else:
                    st.error(result.get("error", "Assessment failed"))

        with col_b:
            if st.button("↩️ Simulate RTO"):
                result = api(f"/api/orders/{selected_id}/simulate-rto", method="POST")
                if result.get("success"):
                    st.success("RTO simulated! Now run Recovery Agent.")
                else:
                    st.error(result.get("error", "Failed"))

        with col_c:
            if st.button("🔄 Run Recovery Agent"):
                with st.spinner("Running recovery..."):
                    result = api(f"/api/agents/recover/{selected_id}", method="POST")
                if result.get("success"):
                    st.success(f"Recovery initiated! Code: {result.get('discount_code')}")
                    st.json(result)
                else:
                    st.error(result.get("error", "Recovery failed"))
