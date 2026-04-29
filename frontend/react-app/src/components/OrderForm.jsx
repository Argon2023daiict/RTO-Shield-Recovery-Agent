import { useState } from 'react';

function OrderForm({ onCreate }) {
  const [customerPhone, setCustomerPhone] = useState('');
  const [productSku, setProductSku] = useState('ELEC-001');
  const [quantity, setQuantity] = useState(1);
  const [paymentMethod, setPaymentMethod] = useState('cod');
  const [error, setError] = useState(null);

  async function handleSubmit(event) {
    event.preventDefault();
    setError(null);

    if (!customerPhone.trim() || !productSku.trim()) {
      setError('Customer phone and product SKU are required.');
      return;
    }

    onCreate({
      customer_phone: customerPhone,
      items: [{ product_sku: productSku, quantity: Number(quantity) }],
      payment_method: paymentMethod,
    });
  }

  return (
    <div className="panel form-panel">
      <div className="panel-header">
        <h3>Create a New Order</h3>
        <p>Submit a new COD order and send it into the Shield / Recovery pipeline.</p>
      </div>
      <form className="order-form" onSubmit={handleSubmit}>
        <label>
          Customer Phone
          <input
            value={customerPhone}
            onChange={(event) => setCustomerPhone(event.target.value)}
            placeholder="+919876543210"
          />
        </label>

        <label>
          Product SKU
          <input
            value={productSku}
            onChange={(event) => setProductSku(event.target.value)}
            placeholder="ELEC-001"
          />
        </label>

        <div className="form-row">
          <label>
            Quantity
            <input
              type="number"
              min="1"
              value={quantity}
              onChange={(event) => setQuantity(event.target.value)}
            />
          </label>

          <label>
            Payment Method
            <select
              value={paymentMethod}
              onChange={(event) => setPaymentMethod(event.target.value)}
            >
              <option value="cod">COD</option>
              <option value="prepaid">Prepaid</option>
              <option value="partial_cod">Partial COD</option>
            </select>
          </label>
        </div>

        {error && <div className="form-error">{error}</div>}

        <button className="button primary" type="submit">
          Create Order
        </button>
      </form>
    </div>
  );
}

export default OrderForm;
