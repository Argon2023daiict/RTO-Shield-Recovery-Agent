function OrderTable({ orders, onSelect }) {
  if (!orders) {
    return <div className="panel empty-state">Loading orders…</div>;
  }

  return (
    <div className="panel">
      <div className="panel-header">
        <h3>Order List</h3>
        <p>Latest orders from the connected database.</p>
      </div>
      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Order #</th>
              <th>Customer</th>
              <th>Amount</th>
              <th>Payment</th>
              <th>Risk</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {orders.map((order) => (
              <tr key={order.id} onClick={() => onSelect(order)}>
                <td>{order.order_number}</td>
                <td>{order.customer_name}</td>
                <td>₹{order.total_amount.toFixed(2)}</td>
                <td>{order.payment_method.toUpperCase()}</td>
                <td>{order.risk_level || 'N/A'}</td>
                <td>{order.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default OrderTable;
