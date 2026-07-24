import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Send, Bot, User, Sparkles } from 'lucide-react';
import { sendCopilotQuery } from '../services/api';
import './CopilotChat.css';

const CopilotChat = () => {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Hello! I am your AI Copilot. I have full access to the database. You can ask me to find crime trends, analyze suspect networks, or search for similar FIRs.' }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setInput('');
    setLoading(true);

    try {
      const response = await sendCopilotQuery(userMessage);
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: response.answer || 'I could not process that request.',
        sources: response.sources,
        hint: response.visualization_hint 
      }]);
    } catch (e) {
      setMessages(prev => [...prev, { role: 'assistant', content: 'There was an error communicating with the AI backend.' }]);
    }
    
    setLoading(false);
  };

  return (
    <div className="chat-container animate-fade-in">
      <header className="dashboard-header" style={{ marginBottom: '1rem' }}>
        <h1 className="text-gradient" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Sparkles className="icon-primary" /> AI Copilot
        </h1>
        <p>Natural language queries over the entire state database.</p>
      </header>

      <div className="chat-window glass-card">
        <div className="chat-messages">
          {messages.map((msg, idx) => (
            <div key={idx} className={`chat-bubble-wrapper ${msg.role === 'user' ? 'user-wrapper' : 'assistant-wrapper'}`}>
              <div className="chat-avatar">
                {msg.role === 'user' ? <User size={20} /> : <Bot size={20} className="icon-primary" />}
              </div>
              <div className={`chat-bubble ${msg.role === 'user' ? 'user-bubble' : 'assistant-bubble'}`}>
                <ReactMarkdown remarkPlugins={[remarkGfm]} className="markdown-body">
                  {msg.content}
                </ReactMarkdown>
                
                {msg.hint && (
                  <div className="chat-hint">
                    <strong>Suggested View:</strong> {msg.hint}
                  </div>
                )}
                {msg.sources && msg.sources.length > 0 && (
                  <div className="chat-sources">
                    <strong>Sources:</strong> {msg.sources.join(', ')}
                  </div>
                )}
              </div>
            </div>
          ))}
          {loading && (
            <div className="chat-bubble-wrapper assistant-wrapper">
               <div className="chat-avatar"><Bot size={20} className="icon-primary" /></div>
               <div className="chat-bubble assistant-bubble typing-indicator">
                 <span></span><span></span><span></span>
               </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
        
        <form onSubmit={handleSubmit} className="chat-input-area">
          <input
            type="text"
            className="chat-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask anything about crime data..."
            disabled={loading}
          />
          <button type="submit" className="chat-send-btn" disabled={!input.trim() || loading}>
            <Send size={20} />
          </button>
        </form>
      </div>
    </div>
  );
};

export default CopilotChat;
