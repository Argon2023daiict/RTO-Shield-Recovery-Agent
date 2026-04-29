"""
🛡️ RTO Shield & Recovery - Agentic Dashboard
A Streamlit-based interactive dashboard for merchants to monitor,
query, and control the AI agent system.
"""

import streamlit as st
import requests
import json
import time
from datetime import datetime

# Configuration
BACKEND_URL = "http://localhost:8000"

st.set_page_config(
    page_title="RTO Shield & Recovery Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        border-radius: 10px;
        padding: 1.2rem;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    .risk-high { color: #e74c3c; font-weight: bold; }
    .risk-medium { color: #f39c12; font-weight: bold; }
    .risk-low { color: #27ae60; font-weight: bold; }
    .risk-critical { color: #8e44ad; font-weight: bold; }
    .stChatMessage { border-radius: 12px; }
    .agent-badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .shield-badge { background-color: #3498db22; color: #3498db; }
    .recovery-badge { background-color: #2ecc7122; color: #2ecc71; }
</style>
""", unsafe_allow_html=True)


def api_call(endpoint: str, method: str = "GET", data: dict = None) -> dict:
    """Make API call to the backend."""
    url = f"{BACKEND_URL}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, timeout=60)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=120)
        else:
            return {"error": f"Unsupported method: {method}"}

        return response.json()
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot connect to backend. Is it running on localhost:8000?"}
    except requests.exceptions.Timeout:
        return {"error": "Request timed out. Agent may still be processing."}
    except Exception as e:
        return {"error": str(e)}


def get_risk_badge(risk_level: str) -> str:
    """Get colored risk badge HTML."""
    colors = {
        "low": ("🟢", "risk-low"),
        "medium": ("🟡", "risk-medium"),
        "high": ("🔴", "risk-high"),
        "critical": ("🟣", "risk-critical"),
    }
    emoji, css_class = colors.get(risk_level.lower(), ("⚪", ""))
    return f'{emoji} <span class="{css_class}">{risk_level.upper()}</span>'


# ==================== SIDEBAR ====================
with st.sidebar:
    st.markdown("## 🛡️ RTO Shield")
    st.markdown("---")

    page = st.radio(
        "Navigate",
        ["📊 Dashboard", "🤖 Agent Chat", "📦 Orders", "⚡ Agent Actions", "🧪 Testing Lab"],
        index=0,
    )

    st.markdown("---")
    st.markdown("### System Status")

    # Health check
    health = api_call("/health")
    if "error" not in health:
        st.success("✅ Backend Online")
        st.caption(f"LLM: {health.get('llm_provider', 'N/A')} / {health.get('llm_model', 'N/A')}")
    else:
        st.error("❌ Backend Offline")
        st.caption(health.get("error", ""))

    st.markdown("---")
    st.markdown(
        "Built with ❤️ using\n"
        "CrewAI + Claude + FastAPI + Razorpay"
    )


# ==================== PAGE: DASHBOARD ====================
if page == "📊 Dashboard":
    st.markdown('<p class="main-header">📊 RTO Shield Analytics Dashboard</p>', unsafe_allow_html=True)
    st.caption("Real-time overview of order risk, RTO impact, and agent performance")

    # Fetch analytics
    analytics = api_call("/api/dashboard/analytics/summary")

    if "error" in analytics:
        st.error(f"Failed to load analytics: {analytics['error']}")
    else:
        # Top-level metrics
        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            st.metric(
                "Total Orders",
                analytics.get("orders", {}).get("total", 0),
                help="All orders in the system"
            )
        with col2:
            st.metric(
                "COD Orders",
                analytics.get("orders", {}).get("cod", 0),
                f"{analytics.get('orders', {}).get('cod_percentage', 0)}%"
            )
        with col3:
            rto_data = analytics.get("rto", {})
            st.metric(
                "RTO Orders",
                rto_data.get("total_rto_orders", 0),
                f"{rto_data.get('rto_rate', 0)}% rate",
                delta_color="inverse"
            )
        with col4:
            st.metric(
                "Shipping Losses",
                f"₹{rto_data.get('total_shipping_lost', 0):,.0f}",
                delta_color="inverse"
            )
        with col5:
            shield = analytics.get("shield_performance", {})
            st.metric(
                "Estimated Savings",
                f"₹{shield.get('estimated_savings', 0):,.0f}",
                f"{shield.get('orders_blocked', 0)} blocked"
            )

        st.markdown("---")

        # Two-column layout
        left_col, right_col = st.columns(2)

        with left_col:
            st.subheader("📊 Risk Distribution")
            risk_dist = analytics.get("risk_distribution", {})
            if risk_dist:
                import plotly.graph_objects as go
                fig = go.Figure(data=[go.Pie(
                    labels=[k.upper() for k in risk_dist.keys()],
                    values=list(risk_dist.values()),
                    hole=0.4,
                    marker_colors=["#27ae60", "#f39c12", "#e74c3c", "#8e44ad"],
                )])
                fig.update_layout(
                    height=350,
                    margin=dict(l=20, r=20, t=20, b=20),
                    showlegend=True,
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                                st.info("No risk data available yet. Assess some orders first!")

            st.subheader("🔄 Recovery Performance")
            recovery = analytics.get("recovery", {})
            rec_col1, rec_col2, rec_col3 = st.columns(3)
            with rec_col1:
                st.metric("Attempted", recovery.get("attempted", 0))
            with rec_col2:
                st.metric("Successful", recovery.get("successful", 0))
            with rec_col3:
                st.metric("Success Rate", recovery.get("success_rate", "0%"))

        with right_col:
            st.subheader("📋 Order Status Breakdown")
            status_dist = analytics.get("status_distribution", {})
            if status_dist:
                import plotly.express as px
                import pandas as pd

                df = pd.DataFrame([
                    {"Status": k.replace("_", " ").title(), "Count": v}
                    for k, v in status_dist.items()
                ])
                fig = px.bar(
                    df, x="Status", y="Count",
                    color="Count",
                    color_continuous_scale="Viridis",
                )
                fig.update_layout(
                    height=350,
                    margin=dict(l=20, r=20, t=20, b=20),
                    xaxis_tickangle=-45,
                    showlegend=False,
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No order data available yet.")

            st.subheader("🤖 Agent Activity")
            agent_data = analytics.get("agent_activity", {})
            ag_col1, ag_col2, ag_col3 = st.columns(3)
            with ag_col1:
                st.metric("Total Actions", agent_data.get("total_actions", 0))
            with ag_col2:
                st.metric("🛡️ Shield", agent_data.get("shield_agent_actions", 0))
            with ag_col3:
                st.metric("🔄 Recovery", agent_data.get("recovery_agent_actions", 0))

        # High-risk orders table
        st.markdown("---")
        st.subheader("🔴 High-Risk Orders Requiring Attention")

        high_risk = api_call("/api/dashboard/analytics/high-risk-orders?limit=10")
        if isinstance(high_risk, list) and len(high_risk) > 0:
            import pandas as pd
            df = pd.DataFrame(high_risk)

            # Format for display
            display_cols = ["order_number", "customer_name", "amount", "risk_score", "risk_level", "status"]
            available_cols = [c for c in display_cols if c in df.columns]

            if available_cols:
                display_df = df[available_cols].copy()
                display_df.columns = ["Order #", "Customer", "Amount (₹)", "Risk Score", "Risk Level", "Status"][:len(available_cols)]
                st.dataframe(
                    display_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Amount (₹)": st.column_config.NumberColumn(format="₹%.2f"),
                        "Risk Score": st.column_config.ProgressColumn(
                            min_value=0, max_value=100, format="%.1f"
                        ),
                    },
                )
            else:
                st.json(high_risk)
        elif isinstance(high_risk, dict) and "error" in high_risk:
            st.warning(f"Could not load high-risk orders: {high_risk['error']}")
        else:
            st.success("✅ No high-risk orders found! All clear.")


# ==================== PAGE: AGENT CHAT ====================
elif page == "🤖 Agent Chat":
    st.markdown('<p class="main-header">🤖 Agentic Dashboard Chat</p>', unsafe_allow_html=True)
    st.caption(
        "Ask questions about your orders, risk, and recovery in natural language. "
        "Powered by AI agents."
    )

    # Example queries
    st.markdown("**Try asking:**")
    example_cols = st.columns(3)
    with example_cols[0]:
        if st.button("📊 Top 5 high-risk orders?", use_container_width=True):
            st.session_state["chat_input"] = "What are my top 5 high-risk COD orders today?"
    with example_cols[1]:
        if st.button("💰 RTO losses this month?", use_container_width=True):
            st.session_state["chat_input"] = "How much have I lost to RTO this month?"
    with example_cols[2]:
        if st.button("🔄 Recovery success rate?", use_container_width=True):
            st.session_state["chat_input"] = "Show me the recovery success rate and breakdown"

    st.markdown("---")

    # Chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Display chat history
    for message in st.session_state.chat_history:
        role = message["role"]
        with st.chat_message(role):
            st.markdown(message["content"])

    # Chat input
    default_input = st.session_state.pop("chat_input", None)
    user_input = st.chat_input("Ask me anything about your orders and RTO data...")

    # Use default input from button if available
    query = default_input or user_input

    if query:
        # Add user message
        st.session_state.chat_history.append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.markdown(query)

        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("🤔 Analyzing your data..."):
                response = api_call(
                    "/api/dashboard/chat",
                    method="POST",
                    data={"message": query}
                )

                if "error" in response and "response" not in response:
                    ai_response = f"❌ Error: {response['error']}"
                else:
                    ai_response = response.get("response", "I couldn't process that query. Please try again.")

                st.markdown(ai_response)

        # Add AI response to history
        st.session_state.chat_history.append({"role": "assistant", "content": ai_response})

    # Clear chat button
    if st.session_state.chat_history:
        if st.button("🗑️ Clear Chat History"):
            st.session_state.chat_history = []
            st.rerun()


# ==================== PAGE: ORDERS ====================
elif page == "📦 Orders":
    st.markdown('<p class="main-header">📦 Order Management</p>', unsafe_allow_html=True)

    # Filters
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    with filter_col1:
        status_filter = st.selectbox(
            "Filter by Status",
            ["All", "pending", "risk_assessed", "approved", "flagged", "cancelled",
             "dispatched", "delivered", "rto_initiated", "rto_received",
             "recovery_initiated", "recovered"],
        )
    with filter_col2:
        risk_filter = st.selectbox(
            "Filter by Risk Level",
            ["All", "low", "medium", "high", "critical"],
        )
    with filter_col3:
        limit = st.number_input("Max Results", min_value=5, max_value=200, value=50)

    # Build query params
    params = f"?limit={limit}"
    if status_filter != "All":
        params += f"&status={status_filter}"
    if risk_filter != "All":
        params += f"&risk_level={risk_filter}"

    # Fetch orders
    orders = api_call(f"/api/orders/{params}")

    if isinstance(orders, list):
        st.markdown(f"**Showing {len(orders)} orders**")

        if orders:
            import pandas as pd

            df = pd.DataFrame(orders)
            display_cols = [c for c in ["order_number", "customer_name", "total_amount",
                                        "payment_method", "status", "risk_score", "risk_level"]
                           if c in df.columns]

            if display_cols:
                display_df = df[display_cols].copy()

                st.dataframe(
                    display_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "total_amount": st.column_config.NumberColumn(
                            "Amount (₹)", format="₹%.2f"
                        ),
                        "risk_score": st.column_config.ProgressColumn(
                            "Risk Score", min_value=0, max_value=100, format="%.1f"
                        ),
                    },
                )

            # Order detail viewer
            st.markdown("---")
            st.subheader("🔍 Order Detail Viewer")

            order_ids = {o.get("order_number", ""): o.get("id", "") for o in orders}
            selected_order = st.selectbox(
                "Select an order to view details",
                options=list(order_ids.keys()),
            )

            if selected_order and order_ids[selected_order]:
                detail = api_call(f"/api/orders/{order_ids[selected_order]}")
                if "error" not in detail:
                    det_col1, det_col2 = st.columns(2)

                    with det_col1:
                        st.markdown("**📋 Order Info**")
                        st.json({
                            "Order #": detail.get("order_number"),
                            "Amount": f"₹{detail.get('total_amount', 0):.2f}",
                            "Status": detail.get("status"),
                            "Payment": detail.get("payment_method"),
                            "Created": detail.get("created_at"),
                        })

                        st.markdown("**👤 Customer**")
                        st.json(detail.get("customer", {}))

                    with det_col2:
                        st.markdown("**🛡️ Risk Assessment**")
                        risk = detail.get("risk_assessment", {})
                        if risk.get("risk_score") is not None:
                            st.metric("Risk Score", f"{risk['risk_score']:.1f}/100")
                            risk_level = risk.get("risk_level", "unknown")
                            st.markdown(get_risk_badge(risk_level), unsafe_allow_html=True)
                            if risk.get("risk_factors"):
                                st.markdown("**Risk Factors:**")
                                for factor in risk["risk_factors"][:5]:
                                    st.markdown(f"- ⚠️ {factor}")
                        else:
                            st.info("Not yet assessed")

                        st.markdown("**🔄 Recovery**")
                        recovery = detail.get("recovery", {})
                        st.json(recovery)
                else:
                    st.error(f"Failed to load detail: {detail.get('error')}")
        else:
            st.info("No orders match the current filters.")
    elif isinstance(orders, dict) and "error" in orders:
        st.error(f"Failed to load orders: {orders['error']}")


# ==================== PAGE: AGENT ACTIONS ====================
elif page == "⚡ Agent Actions":
    st.markdown('<p class="main-header">⚡ Agent Action Log</p>', unsafe_allow_html=True)
    st.caption("Complete audit trail of every action taken by AI agents")

    # Filters
    agent_col1, agent_col2 = st.columns(2)
    with agent_col1:
        agent_filter = st.selectbox(
            "Filter by Agent",
            ["All", "shield_agent", "recovery_agent"],
        )
    with agent_col2:
        action_limit = st.number_input("Max Actions", min_value=5, max_value=200, value=50, key="action_limit")

    params = f"?limit={action_limit}"
    if agent_filter != "All":
        params += f"&agent_name={agent_filter}"

    actions = api_call(f"/api/agents/actions{params}")

    if isinstance(actions, list):
        st.markdown(f"**{len(actions)} agent actions recorded**")

        for action in actions:
            agent_name = action.get("agent_name", "unknown")
            badge_class = "shield-badge" if "shield" in agent_name else "recovery-badge"
            agent_emoji = "🛡️" if "shield" in agent_name else "🔄"

            with st.expander(
                f"{agent_emoji} {action.get('action_type', 'unknown').replace('_', ' ').title()} "
                f"| Order: {action.get('order_id', 'N/A')[:8]}... "
                f"| {action.get('created_at', 'N/A')[:19]}"
            ):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown(f"**Agent:** {agent_name}")
                with col2:
                    confidence = action.get("confidence_score")
                    st.markdown(
                        f"**Confidence:** {confidence:.0%}" if confidence else "**Confidence:** N/A"
                    )
                with col3:
                    success = action.get("success", False)
                    st.markdown(f"**Status:** {'✅ Success' if success else '❌ Failed'}")

                if action.get("reasoning_preview"):
                    st.markdown("**Reasoning:**")
                    st.text(action["reasoning_preview"])

                if action.get("error_message"):
                    st.error(f"Error: {action['error_message']}")
    elif isinstance(actions, dict) and "error" in actions:
        st.error(f"Failed to load actions: {actions['error']}")


# ==================== PAGE: TESTING LAB ====================
elif page == "🧪 Testing Lab":
    st.markdown('<p class="main-header">🧪 Agent Testing Lab</p>', unsafe_allow_html=True)
    st.caption("Create test orders and trigger agent actions to see the system in action")

    tab1, tab2, tab3, tab4 = st.tabs([
        "🛒 Create Order",
        "🛡️ Assess Order",
        "📦 Simulate RTO",
        "🔄 Trigger Recovery"
    ])

    # ---- TAB 1: Create Order ----
    with tab1:
        st.subheader("Create a New COD Order")
        st.markdown("Simulate a new order from an e-commerce platform.")

        create_col1, create_col2 = st.columns(2)

        with create_col1:
            customer_phone = st.selectbox(
                "Customer Phone",
                [
                    "+919876543210 (Priya Sharma - Low Risk)",
                    "+919876543213 (Vikram Patel - Medium Risk)",
                    "+919876543215 (Suresh Singh - High Risk)",
                    "+919876543216 (New User 7891 - Very High Risk)",
                    "+919876543217 (Rohit Gupta - Critical Risk)",
                    "+919876543218 (Deepa Menon - VIP Customer)",
                ],
            )
            phone = customer_phone.split(" ")[0]

        with create_col2:
            products = st.multiselect(
                "Products",
                [
                    "ELEC-001 (Wireless Earbuds - ₹2499)",
                    "FASH-001 (Cotton Kurta Set - ₹1299)",
                    "HOME-001 (Water Bottle - ₹599)",
                    "BEAU-001 (Face Wash - ₹349)",
                    "FASH-002 (Running Shoes - ₹2999)",
                ],
                default=["ELEC-001 (Wireless Earbuds - ₹2499)"],
            )

        if st.button("🛒 Create Order", type="primary", use_container_width=True):
            items = [{"product_sku": p.split(" ")[0], "quantity": 1} for p in products]

            with st.spinner("Creating order..."):
                result = api_call(
                    "/api/orders/",
                    method="POST",
                    data={
                        "customer_phone": phone,
                        "items": items,
                        "payment_method": "cod",
                    }
                )

            if result.get("success"):
                st.success(
                    f"✅ Order Created: **{result['order_number']}** | "
                    f"Amount: **₹{result['total_amount']:.2f}** | "
                    f"Status: {result['status']}"
                )
                st.info(f"Next step: Assess this order → `{result.get('next_step', '')}`")
                st.session_state["last_order_id"] = result.get("order_id")
            else:
                st.error(f"❌ Failed: {result.get('error', result.get('detail', 'Unknown error'))}")

    # ---- TAB 2: Assess Order ----
    with tab2:
        st.subheader("🛡️ Trigger Shield Agent Assessment")
        st.markdown("Run the AI Shield Agent on an order to assess RTO risk.")

        order_id_assess = st.text_input(
            "Order ID to Assess",
            value=st.session_state.get("last_order_id", ""),
            placeholder="Paste an order UUID here",
            key="assess_input",
        )

        if st.button("🛡️ Run Shield Agent", type="primary", use_container_width=True):
            if not order_id_assess:
                st.warning("Please enter an Order ID")
            else:
                with st.spinner("🤖 Shield Agent is analyzing the order... This may take 30-60 seconds."):
                    start_time = time.time()
                    result = api_call(f"/api/agents/assess/{order_id_assess}", method="POST")
                    elapsed = time.time() - start_time

                if result.get("success"):
                    st.success(f"✅ Assessment Complete in {elapsed:.1f}s")

                    # Display results
                    res_col1, res_col2, res_col3 = st.columns(3)
                    with res_col1:
                        score = result.get("risk_score", 0)
                        st.metric("Risk Score", f"{score:.1f}/100")
                    with res_col2:
                        level = result.get("risk_level", "UNKNOWN")
                        st.markdown(f"### {get_risk_badge(level)}", unsafe_allow_html=True)
                    with res_col3:
                        action = result.get("recommended_action", "N/A")
                        action_emojis = {
                            "APPROVE": "✅",
                            "FLAG_FOR_REVIEW": "🟡",
                            "REQUEST_PREPAYMENT": "💳",
                            "RECOMMEND_CANCELLATION": "🚫",
                        }
                        emoji = action_emojis.get(action, "❓")
                        st.metric("Action", f"{emoji} {action}")

                    # Full assessment details
                    with st.expander("📋 Full Assessment Details"):
                        st.json(result.get("assessment", result))

                    st.session_state["last_assessed_order_id"] = order_id_assess
                else:
                    st.error(f"❌ Assessment Failed: {result.get('error', result.get('detail', 'Unknown'))}")

        # Batch assessment
        st.markdown("---")
        st.markdown("### 📦 Batch Assessment")
        batch_limit = st.slider("Orders to assess", 1, 20, 5, key="batch_assess_slider")
        if st.button("🛡️ Assess All Pending Orders", use_container_width=True):
            with st.spinner(f"Assessing up to {batch_limit} pending orders..."):
                result = api_call(
                    f"/api/agents/assess-batch?limit={batch_limit}",
                    method="POST"
                )
            if "total_processed" in result:
                st.success(
                    f"✅ Processed: {result['total_processed']} | "
                    f"✅ Success: {result['successful']} | "
                    f"❌ Failed: {result['failed']}"
                )
                with st.expander("Details"):
                    st.json(result.get("results", []))
            else:
                st.error(f"Batch failed: {result.get('error', 'Unknown')}")

    # ---- TAB 3: Simulate RTO ----
    with tab3:
        st.subheader("📦 Simulate RTO Event")
        st.markdown("Simulate a Return to Origin event for testing the Recovery Agent.")

        order_id_rto = st.text_input(
            "Order ID to simulate RTO",
            value=st.session_state.get("last_assessed_order_id", ""),
            placeholder="Paste an order UUID here",
            key="rto_input",
        )

        if st.button("📦 Simulate RTO", type="secondary", use_container_width=True):
            if not order_id_rto:
                st.warning("Please enter an Order ID")
            else:
                with st.spinner("Simulating RTO event..."):
                    result = api_call(
                        f"/api/orders/{order_id_rto}/simulate-rto",
                        method="POST"
                    )

                if result.get("success"):
                    st.warning(
                        f"📦 RTO Simulated for **{result['order_number']}** | "
                        f"RTO Cost: **₹{result.get('total_rto_cost', 0):.2f}**"
                    )
                    st.info(f"Next step: Trigger recovery → `{result.get('next_step', '')}`")
                    st.session_state["last_rto_order_id"] = order_id_rto
                else:
                    st.error(f"❌ Failed: {result.get('error', result.get('detail', 'Unknown'))}")

    # ---- TAB 4: Trigger Recovery ----
    with tab4:
        st.subheader("🔄 Trigger Recovery Agent")
        st.markdown("Run the AI Recovery Agent to re-engage the customer and salvage revenue.")

        order_id_recover = st.text_input(
            "Order ID to recover",
            value=st.session_state.get("last_rto_order_id", ""),
            placeholder="Paste an order UUID here",
            key="recover_input",
        )

        return_reason = st.selectbox(
            "Return Reason",
            [
                "Customer refused delivery",
                "Customer not available",
                "Incorrect address",
                "Changed mind",
                "Found cheaper elsewhere",
                "Ordered by mistake",
            ],
        )

        if st.button("🔄 Run Recovery Agent", type="primary", use_container_width=True):
            if not order_id_recover:
                st.warning("Please enter an Order ID")
            else:
                with st.spinner("🤖 Recovery Agent is working... This may take 30-60 seconds."):
                    start_time = time.time()
                    result = api_call(
                        f"/api/agents/recover/{order_id_recover}?return_reason={return_reason}",
                        method="POST"
                    )
                    elapsed = time.time() - start_time

                if result.get("success"):
                    st.success(f"✅ Recovery Initiated in {elapsed:.1f}s")

                    rec_col1, rec_col2 = st.columns(2)
                    with rec_col1:
                        st.markdown(f"**Discount Code:** `{result.get('discount_code', 'N/A')}`")
                        st.markdown(f"**Discount:** {result.get('discount_percent', 'N/A')}% OFF")
                    with rec_col2:
                        st.markdown(f"**Order:** {result.get('order_number', 'N/A')}")
                        st.markdown(f"**Status:** {result.get('recovery_status', 'N/A')}")

                    with st.expander("📋 Full Recovery Details"):
                        st.json(result.get("recovery_result", result))
                else:
                    st.error(f"❌ Recovery Failed: {result.get('error', result.get('detail', 'Unknown'))}")

        # Batch recovery
        st.markdown("---")
        st.markdown("### 📦 Batch Recovery")
        batch_recover_limit = st.slider("Orders to recover", 1, 10, 3, key="batch_recover_slider")
        if st.button("🔄 Recover All Pending RTOs", use_container_width=True):
            with st.spinner(f"Processing up to {batch_recover_limit} RTO recoveries..."):
                result = api_call(
                    f"/api/agents/recover-batch?limit={batch_recover_limit}",
                    method="POST"
                )
            if "total_processed" in result:
                st.success(
                    f"✅ Processed: {result['total_processed']} | "
                    f"✅ Success: {result['successful']} | "
                    f"❌ Failed: {result['failed']}"
                )
                with st.expander("Details"):
                    st.json(result.get("results", []))
            else:
                st.error(f"Batch failed: {result.get('error', 'Unknown')}")