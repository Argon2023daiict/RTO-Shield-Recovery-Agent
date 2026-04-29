function AnalyticsPanel({ summary, highRiskOrders }) {
  if (!summary) {
    return <div className="panel empty-state">Loading dashboard metrics...</div>;
  }

  const { orders, rto, shield_performance, recovery, status_distribution } = summary;

  return (
    <div className="dashboard-grid">
      <section className="metrics-panel">
        <div className="metric-card">
          <h3>Total Orders</h3>
          <strong>{orders.total}</strong>
          <span>COD orders: {orders.cod}</span>
        </div>
        <div className="metric-card">
          <h3>RTO Orders</h3>
          <strong>{rto.total_rto_orders}</strong>
          <span>Rate: {rto.rto_rate}%</span>
        </div>
        <div className="metric-card">
          <h3>Shipping Losses</h3>
          <strong>₹{rto.total_shipping_lost.toFixed(2)}</strong>
          <span>Risk revenue: ₹{rto.total_revenue_at_risk.toFixed(2)}</span>
        </div>
        <div className="metric-card">
          <h3>Recovery Success</h3>
          <strong>{recovery.success_rate}%</strong>
          <span>{recovery.successful} successful</span>
        </div>
        <div className="metric-card">
          <h3>Estimated Savings</h3>
          <strong>₹{shield_performance.estimated_savings.toFixed(2)}</strong>
          <span>Orders blocked: {shield_performance.orders_blocked}</span>
        </div>
      </section>

      <section className="list-panel">
        <div className="panel-header">
          <h3>High Risk Orders</h3>
          <p>Top COD orders with the highest risk score.</p>
        </div>

        {highRiskOrders.length === 0 ? (
          <div className="panel empty-state">No high-risk orders available.</div>
        ) : (
          <ul className="list-group">
            {highRiskOrders.map((order) => (
              <li key={order.order_number} className="list-item">
                <div>
                  <strong>{order.order_number}</strong>
                  <span>{order.customer_name}</span>
                </div>
                <div className="list-meta">
                  <span>{order.risk_level.toUpperCase()}</span>
                  <span>₹{order.amount.toFixed(2)}</span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="status-panel">
        <div className="panel-header">
          <h3>Order Status Breakdown</h3>
          <p>Live snapshot from the database.</p>
        </div>
        <div className="status-list">
          {Object.entries(status_distribution || {}).map(([status, count]) => (
            <div key={status} className="status-item">
              <span>{status.replace(/_/g, ' ').toUpperCase()}</span>
              <strong>{count}</strong>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

export default AnalyticsPanel;
