import { useState, useRef, useEffect } from 'react';
import { sendChatMessage } from '../api.js';

function ChatPanel() {
  const [messages, setMessages] = useState([
    {
      id: 'intro',
      text: 'Namaste! 🙏 Ask me anything about your RTO orders, risk metrics, or recovery performance. Try: "Show all high-risk COD orders" or "What is my RTO rate?"',
      sender: 'bot',
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  async function handleSend() {
    if (!input.trim()) return;

    const userMessage = input.trim();
    setInput('');
    setMessages((prev) => [
      ...prev,
      { id: Date.now(), text: userMessage, sender: 'user' },
    ]);

    setLoading(true);
    try {
      const response = await sendChatMessage(userMessage);
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          text: response.response || response.message || JSON.stringify(response),
          sender: 'bot',
        },
      ]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          text: `Error: ${error.message}`,
          sender: 'error',
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  }

  return (
    <div className="panel chat-panel">
      <div className="panel-header">
        <h3>🤖 Agent Chat</h3>
        <p>Ask the AI agent about orders, risks, recovery, and more.</p>
      </div>

      <div className="chat-container">
        <div className="chat-messages">
          {messages.map((msg) => (
            <div key={msg.id} className={`chat-message ${msg.sender}`}>
              <div className="message-avatar">
                {msg.sender === 'user' ? '👤' : msg.sender === 'error' ? '❌' : '🤖'}
              </div>
              <div className="message-content">
                <p>{msg.text}</p>
              </div>
            </div>
          ))}
          {loading && (
            <div className="chat-message bot">
              <div className="message-avatar">🤖</div>
              <div className="message-content">
                <p className="loading-text">Thinking...</p>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="chat-input-area">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about orders, risks, RTO rate, recovery success..."
            disabled={loading}
          />
          <button onClick={handleSend} disabled={loading || !input.trim()} className="button primary">
            {loading ? 'Sending...' : 'Send'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default ChatPanel;
