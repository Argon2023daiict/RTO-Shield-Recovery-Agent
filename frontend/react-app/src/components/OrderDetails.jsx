function OrderDetails({ order }) {
  if (!order) {
    return (
      <div className="panel empty-state">
        Select an order to view full risk, shipping, and recovery details.
      </div>
    );
  }

  return (
    <div className="panel details-panel">
      <div className="panel-header">
        <h3>Order Details</h3>
        <span className="detail-label">{order.status.toUpperCase()}</span>
      </div>

      <div className="detail-row">
        <strong>Order #</strong>
        <span>{order.order_number}</span>
      </div>
      <div className="detail-row">
        <strong>Total</strong>
        <span>₹{order.total_amount.toFixed(2)}</span>
      </div>
      <div className="detail-row">
        <strong>Customer</strong>
        <span>{order.customer.name} • {order.customer.phone}</span>
      </div>
      <div className="detail-row">
        <strong>Payment Method</strong>
        <span>{order.payment_method.toUpperCase()}</span>
      </div>
      <div className="detail-row">
        <strong>Shipping Address</strong>
        <span>{order.shipping_address.address_line_1}, {order.shipping_address.city}, {order.shipping_address.state} {order.shipping_address.pincode}</span>
      </div>

      <div className="section-title">Risk Assessment</div>
      <div className="detail-row">
        <strong>Risk Score</strong>
        <span>{order.risk_assessment.risk_score ?? 'N/A'}</span>
      </div>
      <div className="detail-row">
        <strong>Risk Level</strong>
        <span>{order.risk_assessment.risk_level?.toUpperCase() || 'N/A'}</span>
      </div>
      <div className="detail-row">
        <strong>Assessed At</strong>
        <span>{order.risk_assessment.assessed_at || 'Not assessed'}</span>
      </div>
      <div className="detail-block">
        <strong>Risk Factors</strong>
        <ul>
          {(order.risk_assessment.risk_factors || []).map((factor, index) => (
            <li key={index}>{factor}</li>
          ))}
          {!(order.risk_assessment.risk_factors || []).length && <li>No risk details available.</li>}
        </ul>
      </div>

      <div className="section-title">RTO & Recovery</div>
      <div className="detail-row">
        <strong>Forward Shipping</strong>
        <span>₹{order.rto_details.forward_shipping_cost?.toFixed(2) ?? '0.00'}</span>
      </div>
      <div className="detail-row">
        <strong>Reverse Shipping</strong>
        <span>₹{order.rto_details.reverse_shipping_cost?.toFixed(2) ?? '0.00'}</span>
      </div>
      <div className="detail-row">
        <strong>Total RTO Cost</strong>
        <span>₹{order.rto_details.total_rto_cost?.toFixed(2) ?? '0.00'}</span>
      </div>
      <div className="detail-row">
        <strong>Recovery Attempted</strong>
        <span>{order.recovery.attempted ? 'Yes' : 'No'}</span>
      </div>
      <div className="detail-row">
        <strong>Discount Code</strong>
        <span>{order.recovery.discount_code || 'N/A'}</span>
      </div>
      <div className="detail-row">
        <strong>Payment Link</strong>
        <span>{order.recovery.payment_link ? <a href={order.recovery.payment_link} target="_blank" rel="noreferrer">Open Link</a> : 'N/A'}</span>
      </div>
    </div>
  );
}

export default OrderDetails;
