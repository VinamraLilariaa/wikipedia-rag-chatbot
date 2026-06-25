import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import './App.css';

const API_URL = ''; // Relative for HuggingFace deployment

const SUGGESTIONS = [
  "Virat Kohli Test Stats",
  "History of Eiffel Tower",
  "How black holes work",
  "First moon landing"
];

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, loading]);

  const handleSend = async (text) => {
    const trimmed = text || input.trim();
    if (!trimmed) return;

    const userMsg = { role: 'user', text: trimmed };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const response = await axios.post(`${API_URL}/ask`, {
        question: trimmed,
        history: messages.slice(-5)
      });
      
      const botMsg = { 
        role: 'bot', 
        data: {
          answer: response.data.answer,
          article: response.data.article,
          wikipedia_url: response.data.wikipedia_url,
          images: response.data.images,
          matchedQuery: response.data.matched_query,
          error: response.data.error
        }
      };
      setMessages(prev => [...prev, botMsg]);
    } catch (err) {
      setMessages(prev => [...prev, { role: 'bot', data: { error: "Service unavailable. Please retry." } }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand">
          <div className="brand-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>
          </div>
          <h1>Wiki Intel</h1>
        </div>
        <button className="clear-button" onClick={() => setMessages([])}>New Session</button>
      </header>

      <div className="chat-area" ref={scrollRef}>
        <div className="messages">
          {messages.length === 0 ? (
            <div className="empty-state">
              <h1>Search Wikipedia</h1>
              <p>Get instant answers from the world's largest encyclopedia.</p>
              <div className="suggestions">
                {SUGGESTIONS.map(s => (
                  <button key={s} className="suggestion-chip" onClick={() => handleSend(s)}>{s}</button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((m, i) => (
              <div key={i} className={`message message-${m.role}`}>
                <div className={`bubble bubble-${m.role}`}>
                  {m.role === 'user' ? m.text : (
                    <>
                      <div className="secondary-header">
                        <span>{m.data.article ? `Results for "${m.data.article}"` : "Intelligence"}</span>
                        {m.data.wikipedia_url && (
                          <a href={m.data.wikipedia_url} target="_blank" rel="noreferrer" className="wiki-link">Wiki ↗</a>
                        )}
                      </div>
                      {m.data.error ? <p className="error-text">{m.data.error}</p> : (
                        <>
                          <p>{m.data.answer}</p>
                          {m.data.images && m.data.images.length > 0 && (
                            <div className="image-gallery">
                              {m.data.images.map((img, idx) => (
                                <div key={idx} className="image-tile">
                                  <img src={img.url} alt="wiki" />
                                </div>
                              ))}
                            </div>
                          )}
                        </>
                      )}
                    </>
                  )}
                </div>
              </div>
            ))
          )}
          {loading && <div className="message message-bot"><div className="bubble bubble-bot">Searching intelligence...</div></div>}
        </div>
      </div>

      <div className="composer">
        <div className="composer-box">
          <textarea 
            rows="1" 
            placeholder="Type a question..." 
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), handleSend())}
          />
          <button className="send-button" onClick={() => handleSend()}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/></svg>
          </button>
        </div>
        <p className="disclaimer">Answers grounded in Wikipedia content.</p>
      </div>
    </div>
  );
}

export default App;