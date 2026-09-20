import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { askQuestion } from "../api";
import SourceList from "./SourceList";
import { ErrorIcon } from "./StatusIcons";

/**
 * Step 2 of the UI: a chat-style Q&A view for one indexed repo.
 *
 * Each submit calls POST /repos/{repo_id}/ask (embeds the question,
 * retrieves chunks from ChromaDB, asks Groq, and — on the backend —
 * saves the pair to SQLite for the History tab). This component only
 * renders what comes back; it has no idea ChromaDB or Groq exist.
 */
export default function Chat({ repoId, repoName }) {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const logRef = useRef(null);

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [messages, loading]);

  async function handleSubmit(event) {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || loading) return;

    setQuestion("");
    setLoading(true);
    try {
      const data = await askQuestion(repoId, trimmed);
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          question: trimmed,
          answer: data.answer,
          sources: data.sources,
          isError: false,
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          question: trimmed,
          answer: err.message || "Something went wrong asking the LLM.",
          sources: [],
          isError: true,
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="card">
      <h2>Ask about {repoName}</h2>
      <p className="muted">
        Questions are answered using only the code chunks retrieved for
        this repo — cited below each answer.
      </p>

      <div className="chat-log" ref={logRef}>
        {messages.length === 0 && !loading && (
          <p className="muted">
            e.g. "How does user authentication work?" or "Where is the
            server started?"
          </p>
        )}

        {messages.map((message) => (
          <div key={message.id} className="chat-message">
            <div className="bubble-question">{message.question}</div>
            <div className={"answer-card" + (message.isError ? " is-error" : "")}>
              {message.isError ? (
                <>
                  <ErrorIcon />
                  <span>{message.answer}</span>
                </>
              ) : (
                <div className="markdown">
                  <ReactMarkdown>{message.answer}</ReactMarkdown>
                </div>
              )}
              {!message.isError && <SourceList sources={message.sources} />}
            </div>
          </div>
        ))}

        {loading && (
          <div className="chat-message">
            <div className="answer-card pending">Thinking…</div>
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} className="chat-form">
        <input
          type="text"
          className="text-input"
          placeholder="Ask a question about this codebase…"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          disabled={loading}
        />
        <button type="submit" className="btn" disabled={loading || !question.trim()}>
          Ask
        </button>
      </form>
    </section>
  );
}
