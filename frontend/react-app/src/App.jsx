import { useEffect, useState } from 'react';
import AnalyticsPanel from './components/AnalyticsPanel.jsx';
import OrderForm from './components/OrderForm.jsx';
import OrderTable from './components/OrderTable.jsx';
import OrderDetails from './components/OrderDetails.jsx';
import ChatPanel from './components/ChatPanel.jsx';
import {
  fetchAnalytics,
  fetchOrders,
  fetchOrderDetail,
  createOrder,
  fetchHighRiskOrders,
} from './api.js';

const pages = ['Dashboard', 'Orders', 'Agent Chat', 'Create Order'];

function App() {
  const [page, setPage] = useState('Dashboard');
  const [analytics, setAnalytics] = useState(null);
  const [highRiskOrders, setHighRiskOrders] = useState([]);
  const [orders, setOrders] = useState([]);
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [statusMessage, setStatusMessage] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (page === 'Dashboard') {
      loadDashboard();
    }
    if (page === 'Orders') {
      loadOrders();
    }
  }, [page]);

  async function loadDashboard() {
    setStatusMessage(null);
    setError(null);
    setLoading(true);
    try {
      const summary = await fetchAnalytics();
      const highRisk = await fetchHighRiskOrders(8);
      setAnalytics(summary);
      setHighRiskOrders(highRisk);
    } catch (err) {
      setError(err.message || 'Unable to load dashboard');
    } finally {
      setLoading(false);
    }
  }

  async function loadOrders() {
    setStatusMessage(null);
    setError(null);
    setSelectedOrder(null);
    setLoading(true);
    try {
      const orderList = await fetchOrders(25, 0);
      setOrders(orderList);
    } catch (err) {
      setError(err.message || 'Unable to load orders');
    } finally {
      setLoading(false);
    }
  }

  async function handleOrderSelect(order) {
    setError(null);
    setStatusMessage(null);
    setLoading(true);
    try {
      const detail = await fetchOrderDetail(order.id);
      setSelectedOrder(detail);
    } catch (err) {
      setError(err.message || 'Unable to load order detail');
    } finally {
      setLoading(false);
    }
  }

  async function handleCreateOrder(payload) {
    setError(null);
    setStatusMessage(null);
    setLoading(true);
    try {
      const response = await createOrder(payload);
      setStatusMessage(response.message || 'Order created successfully');
      setPage('Orders');
      await loadOrders();
    } catch (err) {
      setError(err.message || 'Unable to create order');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-badge">RTO</span>
          <div>
            <h1>Shield UI</h1>
            <p>React dashboard for the recovery pipeline</p>
          </div>
        </div>

        <nav className="nav-menu">
          {pages.map((item) => (
            <button
              key={item}
              className={page === item ? 'nav-item active' : 'nav-item'}
              onClick={() => setPage(item)}
            >
              {item}
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <p>Backend: http://localhost:8000</p>
          <p>React: http://localhost:3000</p>
        </div>
      </aside>

      <main className="content">
        <header className="page-header">
          <div>
            <h2>{page}</h2>
            <p>
              {page === 'Dashboard'
                ? 'Real-time metrics, risk signals, and recovery performance.'
                : page === 'Orders'
                ? 'Browse orders and inspect risk, RTO, and recovery details.'
                : page === 'Agent Chat'
                ? 'Chat with the AI agent about orders, risks, RTO rates, and recovery metrics.'
                : 'Create a new COD order and send it through the agent pipeline.'}
            </p>
          </div>
          <div className="header-meta">
            {loading && <span className="badge badge-loading">Loading…</span>}
            {error && <span className="badge badge-error">{error}</span>}
            {statusMessage && <span className="badge badge-success">{statusMessage}</span>}
          </div>
        </header>

        {page === 'Dashboard' && (
          <AnalyticsPanel summary={analytics} highRiskOrders={highRiskOrders} />
        )}

        {page === 'Orders' && (
          <div className="orders-grid">
            <section className="orders-panel">
              <OrderTable orders={orders} onSelect={handleOrderSelect} />
            </section>
            <section className="order-detail-panel">
              <OrderDetails order={selectedOrder} />
            </section>
          </div>
        )}

        {page === 'Agent Chat' && <ChatPanel />}

        {page === 'Create Order' && <OrderForm onCreate={handleCreateOrder} />}
      </main>
    </div>
  );
}

export default App;
