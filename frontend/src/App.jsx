import { useEffect, useRef, useState } from "react";
import axios from "axios";
import "./App.css";

const SUGGESTIONS = [
  "Who is Virat Kohli?",
  "Tell me about the Eiffel Tower",
  "What is the history of Python?",
  "Explain the theory of relativity",
];

function Avatar({ role }) {
  return (
    <div className={`avatar avatar-${role}`}>
      {role === "user" ? (
        <svg
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            d="M12 12a4.5 4.5 0 1 0 0-9 4.5 4.5 0 0 0 0 9Zm0 2.25c-4.142 0-7.5 2.515-7.5 5.625v.375a.75.75 0 0 0 .75.75h13.5a.75.75 0 0 0 .75-.75v-.375c0-3.11-3.358-5.625-7.5-5.625Z"
            fill="currentColor"
          />
        </svg>
      ) : (
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M12 6.04A8.97 8.97 0 0 0 6 3.75c-1.05 0-2.06.18-3 .51v14.25A8.99 8.99 0 0 1 6 18c2.3 0 4.41.87 6 2.29m0-14.25a8.97 8.97 0 0 1 6-2.29c1.05 0 2.06.18 3 .51v14.25A8.99 8.99 0 0 0 18 18a8.97 8.97 0 0 0-6 2.29m0-14.25v14.25" />
        </svg>
      )}
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="message message-bot">
      <Avatar role="bot" />

      <div className="bubble bubble-bot typing-bubble">
        <span className="dot"></span>
        <span className="dot"></span>
        <span className="dot"></span>
      </div>
    </div>
  );
}

function SourcesPanel({ sources }) {
  const [open, setOpen] = useState(false);

  if (!sources || sources.length === 0) return null;

  return (
    <div className="sources-panel">
      <button
        className="link-button"
        onClick={() => setOpen(!open)}
      >
        {open
          ? "Hide retrieved context ▲"
          : `Show retrieved context (${Math.min(
              sources.length,
              3
            )}) ▼`}
      </button>

      {open && (
        <div className="sources-list">
          {sources.slice(0, 3).map((chunk, index) => (
            <div className="chunk" key={index}>
              <strong>Chunk {index + 1}</strong>
              <p>{chunk}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ImageGallery({ images }) {
  if (!images || images.length === 0) return null;

  return (
    <div className="image-gallery">
      {images.map((img, index) => (
        <a
          key={index}
          href={img.url}
          target="_blank"
          rel="noreferrer"
          className="image-tile"
          title={img.caption || ""}
        >
          <img
            src={img.url}
            alt={img.caption || "Wikipedia image"}
            loading="lazy"
          />

          {img.caption && (
            <span className="image-caption">
              {img.caption}
            </span>
          )}
        </a>
      ))}
    </div>
  );
}

function BotMessage({ data }) {
  return (
    <div className="message message-bot">
      <Avatar role="bot" />

      <div className="bubble bubble-bot">
        {data.error ? (
          <p className="error-text">{data.error}</p>
        ) : (
          <>
            {data.spellingCorrected &&
              data.matchedQuery && (
                <p className="spelling-note">
                  Showing results for{" "}
                  <strong>
                    "{data.matchedQuery}"
                  </strong>
                </p>
              )}

            <p className="answer-text">
              {data.answer}
            </p>

            <ImageGallery
              images={data.images}
            />

            <div className="meta-row">
              <a
                className="meta-chip meta-link"
                href={data.wikipedia_url}
                target="_blank"
                rel="noreferrer"
              >
                📖 {data.article}
              </a>

              <span className="meta-chip">
                ⚡ {data.response_time}s
              </span>

              <span className="meta-chip">
                {data.cache_hit
                  ? "💾 Cached"
                  : "🆕 Freshly indexed"}
              </span>

              <span className="meta-chip">
                🤖 {data.model}
              </span>
            </div>

            <SourcesPanel
              sources={data.sources}
            />
          </>
        )}
      </div>
    </div>
  );
}

function UserMessage({ text }) {
  return (
    <div className="message message-user">
      <div className="bubble bubble-user">
        {text}
      </div>

      <Avatar role="user" />
    </div>
  );
}
function App() {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState([]);

  const scrollRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, loading]);

  const sendQuestion = async (text) => {
    const trimmed = (text ?? question).trim();

    if (!trimmed || loading) return;

    setMessages((prev) => [
      ...prev,
      {
        role: "user",
        text: trimmed,
      },
    ]);

    setQuestion("");
    setLoading(true);

    try {
      const API_URL =
        import.meta.env.VITE_API_URL || "/api";

      const response = await axios.post(
        `${API_URL}/ask`,
        {
          question: trimmed,
          history: messages.slice(-5) // Send the last 5 messages for context
        }
      );

      const data = response.data;

      // ---------- Convert backend image into gallery ----------
      if (data.image && !data.images) {
        data.images = [
          {
            url: data.image,
            caption: data.article,
          },
        ];
      }

      // ---------- Ensure images array always exists ----------
      if (!data.images) {
        data.images = [];
      }

      // ---------- Ensure sources always exists ----------
      if (!data.sources) {
        data.sources = [];
      }

      setMessages((prev) => [
        ...prev,
        {
          role: "bot",
          data: {
            ...data,

            spellingCorrected:
              data.spelling_corrected,

            matchedQuery:
              data.matched_query,
          },
        },
      ]);
    } catch (error) {
      const detail =
        error.response?.data?.detail ||
        error.message ||
        "Unable to reach the server.";

      setMessages((prev) => [
        ...prev,
        {
          role: "bot",
          data: {
            error: detail,
          },
        },
      ]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyDown = (e) => {
    if (
      e.key === "Enter" &&
      !e.shiftKey
    ) {
      e.preventDefault();
      sendQuestion();
    }
  };

  const clearChat = () => {
    setMessages([]);
  };
    return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand">
          <div className="brand-icon">
             <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="accent-color">
                <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1-2.5-2.5Z" />
                <path d="M8 7h6" /><path d="M8 11h8" /><path d="M8 15h5" />
             </svg>
          </div>

          <div>
            <h1>Wikipedia Intelligence</h1>

            <p>
              AI-powered answers grounded in Wikipedia.
            </p>
          </div>
        </div>

        {messages.length > 0 && (
          <button
            className="clear-button"
            onClick={clearChat}
          >
            New Session
          </button>
        )}
      </header>

      <main
        className="chat-area"
        ref={scrollRef}
      >
        {messages.length === 0 ? (
          <div className="empty-state">

            <div className="empty-icon">
              ✨
            </div>

            <h2>
              Discover the World
            </h2>

            <p>
              Ask a complex question and I'll retrieve the relevant 
              knowledge from Wikipedia to provide a precise answer.
            </p>

            <div className="suggestions">

              {SUGGESTIONS.map((item) => (

                <button
                  key={item}
                  className="suggestion-chip"
                  onClick={() =>
                    sendQuestion(item)
                  }
                >
                  {item}
                </button>

              ))}

            </div>

          </div>
        ) : (

          <div className="messages">

            {messages.map((message, index) =>

              message.role === "user" ? (

                <UserMessage
                  key={index}
                  text={message.text}
                />

              ) : (

                <BotMessage
                  key={index}
                  data={message.data}
                />

              )

            )}

            {loading && <TypingIndicator />}

          </div>

        )}
      </main>

      <footer className="composer">

        <div className="composer-box">

          <textarea
            ref={inputRef}
            autoFocus
            rows={1}
            placeholder="Type your question..."
            value={question}
            onChange={(e) =>
              setQuestion(e.target.value)
            }
            onKeyDown={handleKeyDown}
          />

          <button
            className="send-button"
            onClick={() => sendQuestion()}
            disabled={
              loading ||
              !question.trim()
            }
            aria-label="Send"
          >
            {loading ? (

              <span className="spinner"></span>

            ) : (

              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>

            )}
          </button>

        </div>

        <p className="disclaimer">
          Precision AI — Verified by Wikipedia
        </p>

      </footer>

    </div>
  );
}

export default App;