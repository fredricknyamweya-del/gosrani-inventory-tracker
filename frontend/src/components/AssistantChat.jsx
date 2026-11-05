import {
  ArrowUpRight,
  Bot,
  RotateCcw,
  Send,
  Sparkles,
  Trash2,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router";
import { api } from "../services/api";
import { formatDate } from "../utils/format";
import { Button } from "./ui";

const suggestions = [
  "How many School Shirts are in stock?",
  "Show everything received this week",
  "What went out yesterday?",
  "Show everything in Mattresses",
  "Show everything in Yarns",
];

export default function AssistantChat({ compact = false }) {
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState("");
  const [validationError, setValidationError] = useState("");
  const [pending, setPending] = useState(false);
  const nextId = useRef(0);
  const pendingRef = useRef(false);
  const inputRef = useRef(null);
  const bottomRef = useRef(null);

  useEffect(() => {
    const reducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    bottomRef.current?.scrollIntoView({
      behavior: reducedMotion ? "auto" : "smooth",
      block: "end",
    });
  }, [messages, pending]);

  async function fetchAnswer(question, responseId) {
    try {
      const response = await api.assistantQuery(question);
      setMessages((current) =>
        current.map((message) =>
          message.id === responseId
            ? { ...message, status: "complete", result: response.data }
            : message,
        ),
      );
    } catch (error) {
      setMessages((current) =>
        current.map((message) =>
          message.id === responseId
            ? {
                ...message,
                status: "error",
                error: error.message || "Unable to answer that question.",
              }
            : message,
        ),
      );
    } finally {
      pendingRef.current = false;
      setPending(false);
    }
  }

  function submitQuestion(value = draft) {
    const question = value.trim();
    if (pendingRef.current) return;
    if (!question) {
      setValidationError("Enter a question to get started.");
      inputRef.current?.focus();
      return;
    }
    if (question.length > 500) {
      setValidationError("Keep your question to 500 characters or fewer.");
      inputRef.current?.focus();
      return;
    }

    setValidationError("");
    setDraft("");
    pendingRef.current = true;
    setPending(true);
    const questionId = ++nextId.current;
    const responseId = ++nextId.current;
    setMessages((current) => [
      ...current,
      { id: questionId, role: "user", text: question },
      { id: responseId, role: "assistant", status: "thinking" },
    ]);
    void fetchAnswer(question, responseId);
  }

  function retryQuestion(questionId, responseId) {
    if (pendingRef.current) return;
    const question = messages.find(
      (message) => message.id === questionId,
    )?.text;
    if (!question) return;
    pendingRef.current = true;
    setPending(true);
    setMessages((current) =>
      current.map((message) =>
        message.id === responseId
          ? { ...message, status: "thinking", error: undefined }
          : message,
      ),
    );
    void fetchAnswer(question, responseId);
  }

  function clearConversation() {
    if (pendingRef.current) return;
    setMessages([]);
    setDraft("");
    setValidationError("");
    inputRef.current?.focus();
  }

  function handleInputKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submitQuestion();
    }
  }

  return (
    <section
      aria-label="Read-only inventory assistant"
      className={`assistant-chat${compact ? " assistant-chat-compact" : ""}`}
    >
      <div className="assistant-chat-toolbar">
        <div className="assistant-trust">
          <span className="assistant-readonly">
            <Bot aria-hidden="true" size={14} />
            Read-only
          </span>
          <span className="assistant-disclaimer">
            Verify Important details with actual records if need be
          </span>
        </div>
        <Button
          aria-label="Clear conversation"
          className="assistant-clear"
          disabled={messages.length === 0 || pending}
          onClick={clearConversation}
          variant="ghost"
        >
          <Trash2 aria-hidden="true" size={15} />
          Clear
        </Button>
      </div>

      <div
        aria-live="polite"
        aria-relevant="additions text"
        className="assistant-messages"
        role="log"
      >
        {messages.length === 0 ? (
          <div className="assistant-welcome">
            <span aria-hidden="true" className="assistant-welcome-icon">
              <Sparkles size={20} />
            </span>
            <h2>Ask about your inventory</h2>
            <p>
              I can find records and summarize stock movements using the
              inventory data.
            </p>
            <div aria-label="Suggested questions" className="assistant-suggestions">
              {suggestions.map((suggestion) => (
                <button
                  className="assistant-suggestion"
                  disabled={pending}
                  key={suggestion}
                  onClick={() => submitQuestion(suggestion)}
                  type="button"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <ol className="assistant-message-list">
            {messages.map((message, index) => {
              if (message.role === "user") {
                return (
                  <li className="assistant-message assistant-message-user" key={message.id}>
                    <p>{message.text}</p>
                  </li>
                );
              }

              const priorQuestion = messages
                .slice(0, index)
                .reverse()
                .find((entry) => entry.role === "user");
              const result = message.result;
              const matches = result?.records ?? [];
              const totalMatches = result?.totalMatches ?? 0;

              return (
                <li className="assistant-message assistant-message-bot" key={message.id}>
                  <span aria-hidden="true" className="assistant-avatar">
                    <Sparkles size={15} />
                  </span>
                  <div className="assistant-message-content">
                    {message.status === "thinking" ? (
                      <p aria-label="Thinking" className="assistant-thinking" role="status">
                        <span className="assistant-thinking-dots" />
                        Thinking…
                      </p>
                    ) : message.status === "error" ? (
                      <div className="assistant-error" role="alert">
                        <p>{message.error}</p>
                        <Button
                          disabled={pending}
                          onClick={() =>
                            priorQuestion &&
                            retryQuestion(priorQuestion.id, message.id)
                          }
                          variant="secondary"
                        >
                          <RotateCcw aria-hidden="true" size={15} />
                          Retry
                        </Button>
                      </div>
                    ) : (
                      <>
                        <p className="assistant-answer">{result?.answer}</p>
                        {totalMatches === 0 && (
                          <p className="assistant-no-results">
                            I couldn&apos;t find any matching records.
                          </p>
                        )}
                        {matches.length > 0 && (
                          <div className="assistant-result-list">
                            {matches.map((record) => (
                              <article
                                className="assistant-result-card"
                                key={record.id}
                              >
                                <div className="assistant-result-heading">
                                  <div>
                                    <span>{record.category}</span>
                                    <h3>{record.item}</h3>
                                    <p>{record.size || "No specification"}</p>
                                  </div>
                                  <time dateTime={record.date}>
                                    {formatDate(record.date)}
                                  </time>
                                </div>
                                <div className="assistant-result-quantities">
                                  <span className="assistant-quantity-in">
                                    <strong>Quantity In</strong>
                                    {record.quantityIn ?? "–"}
                                  </span>
                                  <span className="assistant-quantity-out">
                                    <strong>Quantity Out</strong>
                                    {record.quantityOut ?? "–"}
                                  </span>
                                </div>
                                {record.details && (
                                  <p className="assistant-result-details">
                                    {record.details}
                                  </p>
                                )}
                                <Link
                                  className="assistant-record-link"
                                  to={`/inventory/${encodeURIComponent(record.id)}`}
                                >
                                  View record
                                  <ArrowUpRight aria-hidden="true" size={14} />
                                </Link>
                              </article>
                            ))}
                          </div>
                        )}
                        {totalMatches > 5 && (
                          <Link
                            className="assistant-all-results"
                            to={`/inventory?search=${encodeURIComponent(result.searchQuery)}`}
                          >
                            Search Inventory for “{result.searchQuery}”
                            <ArrowUpRight aria-hidden="true" size={15} />
                          </Link>
                        )}
                      </>
                    )}
                  </div>
                </li>
              );
            })}
            <li aria-hidden="true" className="assistant-scroll-anchor" ref={bottomRef} />
          </ol>
        )}
        {messages.length === 0 && <span aria-hidden="true" ref={bottomRef} />}
      </div>

      <form
        className="assistant-composer"
        onSubmit={(event) => {
          event.preventDefault();
          submitQuestion();
        }}
      >
        {validationError && (
          <p className="assistant-validation-error" role="alert">
            {validationError}
          </p>
        )}
        <div className="assistant-input-wrap">
          <label className="sr-only" htmlFor="assistant-question">
            Ask the inventory assistant
          </label>
          <textarea
            id="assistant-question"
            maxLength={501}
            onChange={(event) => {
              setDraft(event.target.value);
              if (validationError) setValidationError("");
            }}
            onKeyDown={handleInputKeyDown}
            placeholder="Ask a question about inventory…"
            ref={inputRef}
            rows={2}
            value={draft}
          />
          <Button
            aria-label="Send question"
            disabled={pending || !draft.trim()}
            type="submit"
          >
            <Send aria-hidden="true" size={16} />
            <span>Send</span>
          </Button>
        </div>
        <p className="assistant-composer-hint">
          Enter to send · Shift + Enter for a new line · 500 characters max
        </p>
      </form>
    </section>
  );
}
