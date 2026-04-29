const BASE_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

async function request(endpoint, options = {}) {
  const response = await fetch(`${BASE_URL}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
    },
    ...options,
  });

  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body.detail || body.error || 'API request failed');
  }
  return body;
}

export function fetchAnalytics() {
  return request('/api/dashboard/analytics/summary');
}

export function fetchOrders(limit = 25, offset = 0) {
  return request(`/api/orders?limit=${limit}&offset=${offset}`);
}

export function fetchOrderDetail(orderId) {
  return request(`/api/orders/${orderId}`);
}

export function createOrder(payload) {
  return request('/api/orders/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function fetchHighRiskOrders(limit = 10) {
  return request(`/api/dashboard/analytics/high-risk-orders?limit=${limit}`);
}

export function sendChatMessage(message) {
  return request('/api/dashboard/chat', {
    method: 'POST',
    body: JSON.stringify({ message }),
  });
}
