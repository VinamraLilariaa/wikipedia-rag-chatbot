import { useState } from "react";
import axios from "axios";
import "./App.css";

function App() {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [showSources, setShowSources] = useState(false);

  const askQuestion = async () => {
    if (!question.trim() || loading) return;

    setLoading(true);
    setResult(null);
    setShowSources(false);

    try {
      const API_URL = import.meta.env.VITE_API_URL || "/api";

      const response = await axios.post(`${API_URL}/ask`, {
        question,
      });

      setResult(response.data);
    } catch (error) {
      console.error(error);

      alert(
        error.response?.data?.detail ||
          "Unable to connect to backend."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container">
      <h1>📚 Wikipedia RAG Chatbot</h1>

      <p className="subtitle">
        Ask anything from Wikipedia and get AI-powered answers.
      </p>

      <div className="searchBox">
        <input
          autoFocus
          type="text"
          placeholder="Ask a question..."
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") askQuestion();
          }}
        />

        <button
          onClick={askQuestion}
          disabled={loading}
        >
          {loading ? "Thinking..." : "Ask"}
        </button>
      </div>

      {loading && (
        <div className="loading">
          <div className="spinner"></div>
          <p>Generating Answer...</p>
        </div>
      )}

      {result && (
        <div className="result">
          <h2>Answer</h2>

          <p className="answer">{result.answer}</p>

          <hr />

          <div className="metadata">
            <p>
              📄 <strong>Article:</strong> {result.article}
            </p>

            <p>
              ⚡ <strong>Response Time:</strong>{" "}
              {result.response_time} sec
            </p>

            <p>
              💾 <strong>Cache:</strong>{" "}
              {result.cache_hit ? "🟢 Hit" : "🔴 Miss"}
            </p>

            <p>
              🤖 <strong>Model:</strong>{" "}
              {result.model}
            </p>

            <a
              href={result.wikipedia_url}
              target="_blank"
              rel="noreferrer"
            >
              📖 Open Wikipedia Article
            </a>
          </div>

          <button
            className="toggleButton"
            onClick={() =>
              setShowSources(!showSources)
            }
          >
            {showSources
              ? "Hide Retrieved Context"
              : "Show Retrieved Context"}
          </button>

          {showSources && (
            <div className="sources">
              {result.sources?.slice(0, 3).map((chunk, index) => (
                <div
                  className="chunk"
                  key={index}
                >
                  <strong>Chunk {index + 1}</strong>

                  <p>{chunk}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default App;