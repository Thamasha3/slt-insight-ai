import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  ArrowUp,
  Bot,
  CalendarDays,
  Check,
  Clock3,
  Copy,
  FileText,
  Network,
  Siren,
  ThumbsDown,
  ThumbsUp,
  User,
} from "lucide-react";
import api from "../services/api.js";
import { useAuth } from "../context/AuthContext.jsx";
import { useChat } from "../context/ChatContext.jsx";

const SUGGESTIONS = [
  { title: "Check 2026 Annual Leave Policy", icon: CalendarDays },
  { title: "Regional Fiber Rollout Progress", icon: Network },
  { title: "Reported Network Escalations", icon: Siren },
  { title: "Customer Service Center Operating Hours", icon: Clock3 },
];

const markdownComponents = {
  h1: ({ children }) => <h1 className="mb-2 text-lg font-semibold text-slate-900">{children}</h1>,
  h2: ({ children }) => <h2 className="mb-2 text-base font-semibold text-slate-900">{children}</h2>,
  h3: ({ children }) => <h3 className="mb-1.5 text-sm font-semibold text-slate-900">{children}</h3>,
  p: ({ children }) => <p className="mb-2 last:mb-0 leading-relaxed">{children}</p>,
  ul: ({ children }) => <ul className="mb-2 list-disc space-y-1 pl-5 last:mb-0">{children}</ul>,
  ol: ({ children }) => <ol className="mb-2 list-decimal space-y-1 pl-5 last:mb-0">{children}</ol>,
  li: ({ children }) => <li className="leading-relaxed">{children}</li>,
  strong: ({ children }) => <strong className="font-semibold text-slate-900">{children}</strong>,
  a: ({ href, children }) => (
    <a href={href} className="font-medium text-teal-700 underline underline-offset-2" target="_blank" rel="noreferrer">
      {children}
    </a>
  ),
  blockquote: ({ children }) => (
    <blockquote className="my-2 border-l-2 border-teal-200 pl-3 text-slate-600">{children}</blockquote>
  ),
  table: ({ children }) => (
    <div className="my-2 overflow-x-auto rounded-lg border border-slate-200">
      <table className="min-w-full text-left text-xs">{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead className="bg-slate-50 text-slate-600">{children}</thead>,
  th: ({ children }) => <th className="px-3 py-2 font-semibold">{children}</th>,
  td: ({ children }) => <td className="border-t border-slate-100 px-3 py-2">{children}</td>,
  code: ({ className, children, ...props }) => {
    const inline = !className;
    if (inline) {
      return (
        <code className="rounded bg-slate-100 px-1 py-0.5 font-mono text-[0.8em] text-teal-800" {...props}>
          {children}
        </code>
      );
    }
    return (
      <code className="block overflow-x-auto rounded-lg bg-slate-900 p-3 font-mono text-xs text-slate-100" {...props}>
        {children}
      </code>
    );
  },
  pre: ({ children }) => <pre className="my-2 overflow-x-auto">{children}</pre>,
};

function proseWithoutBibliography(text) {
  const lines = (text || "").split("\n");
  while (lines.length) {
    const stripped = lines[lines.length - 1].trim();
    if (!stripped) {
      lines.pop();
      continue;
    }
    if (/^\[\d+\](\s+.+)?$/.test(stripped) || /^(sources?|references|citations)\s*:?\s*$/i.test(stripped)) {
      lines.pop();
      continue;
    }
    break;
  }
  return lines.join("\n");
}

function citedIndexesFromAnswer(text) {
  const used = [];
  const seen = new Set();
  const prose = proseWithoutBibliography(text);
  for (const match of prose.matchAll(/\[(\d+(?:\s*,\s*\d+)*)\]|【(\d+)】/g)) {
    const packed = match[1] || match[2] || "";
    for (const part of packed.split(",")) {
      const number = Number(part.trim());
      if (!seen.has(number)) {
        seen.add(number);
        used.push(number);
      }
    }
  }
  return used;
}

function sourcesUsedInAnswer(message) {
  const citations = message.citations || [];
  const used = new Set(citedIndexesFromAnswer(message.content));
  if (used.size === 0) return [];
  return citations.filter((item, index) => used.has(item.citation_index ?? index + 1));
}

function citationLabel(match) {
  const index = match.citation_index;
  const name = match.filename || "Source";
  return index ? `${name} [${index}]` : name;
}

function citationDetail(match) {
  const parts = [];
  if (match.source_page) parts.push(`Page ${match.source_page}`);
  if (match.sheet_name) parts.push(`Sheet ${match.sheet_name}`);
  if (match.source_row) parts.push(`Row ${match.source_row}`);
  if (match.category) parts.push(match.category);
  return parts.join(" · ");
}

function roleSubtitle(user) {
  if (user.role === "SUPER") {
    return "I can assist with approved general, regional, and confidential/internal records. You can also validate knowledge sources.";
  }
  if (user.role === "REGIONAL") {
    return "I can assist with approved general documentation and your regional records.";
  }
  if (user.role === "ADMIN") {
    return "Admin accounts manage users and knowledge. Employee answers stay with Super, Regional, and Normal users.";
  }
  return "I can assist with approved general documentation.";
}

function EmptyState({ user, onHover, onSelect }) {
  return (
    <div className="flex h-full items-center justify-center px-4 py-10">
      <div className="w-full max-w-2xl text-center">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-[#064e3b] text-white shadow-sm">
          <Bot className="h-7 w-7" />
        </div>
        <h2 className="mt-5 text-2xl font-semibold tracking-tight text-slate-900">
          Good day! How can I assist you with SLT operations today?
        </h2>
        <p className="mt-2 text-sm text-slate-500">{roleSubtitle(user)}</p>
        <div className="mt-8 grid gap-3 sm:grid-cols-2">
          {SUGGESTIONS.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.title}
                type="button"
                onMouseEnter={() => onHover(item.title)}
                onFocus={() => onHover(item.title)}
                onClick={() => onSelect(item.title)}
                className="group rounded-2xl border border-slate-200 bg-white p-4 text-left shadow-sm transition duration-200 hover:-translate-y-0.5 hover:border-teal-300 hover:bg-teal-50/60 hover:shadow-md"
              >
                <div className="flex items-start justify-between gap-3">
                  <Icon className="h-5 w-5 text-[#047857] transition group-hover:scale-110" />
                  <ArrowUp className="h-4 w-4 rotate-45 text-slate-300 opacity-0 transition group-hover:opacity-100 group-hover:text-teal-600" />
                </div>
                <p className="mt-3 text-sm font-medium text-slate-800 group-hover:text-[#064e3b]">{item.title}</p>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function AssistantMarkdown({ content }) {
  return (
    <div className="prose-p:leading-relaxed text-sm text-slate-800">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
        {proseWithoutBibliography(content)}
      </ReactMarkdown>
    </div>
  );
}

function MessageActions({ content, messageId, feedback, onFeedback }) {
  const [copied, setCopied] = useState(false);

  async function copyAnswer() {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      /* ignore */
    }
  }

  return (
    <div className="mt-3 flex items-center gap-1">
      <button
        type="button"
        onClick={copyAnswer}
        className="rounded-lg p-1.5 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
        aria-label="Copy response"
      >
        {copied ? <Check className="h-4 w-4 text-[#047857]" /> : <Copy className="h-4 w-4" />}
      </button>
      <button
        type="button"
        onClick={() => onFeedback(messageId, "up")}
        className={`rounded-lg p-1.5 transition hover:bg-slate-100 ${
          feedback === "up" ? "text-[#047857]" : "text-slate-400 hover:text-slate-700"
        }`}
        aria-label="Helpful"
      >
        <ThumbsUp className="h-4 w-4" />
      </button>
      <button
        type="button"
        onClick={() => onFeedback(messageId, "down")}
        className={`rounded-lg p-1.5 transition hover:bg-slate-100 ${
          feedback === "down" ? "text-rose-600" : "text-slate-400 hover:text-slate-700"
        }`}
        aria-label="Not helpful"
      >
        <ThumbsDown className="h-4 w-4" />
      </button>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex items-start gap-3">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#064e3b] text-white">
        <Bot className="h-4 w-4" />
      </div>
      <div className="max-w-[85%] rounded-2xl rounded-tl-sm border border-slate-200/80 bg-white px-5 py-4 shadow-sm">
        <div className="flex items-center gap-2 text-sm text-slate-500">
          <span className="flex gap-1">
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-teal-600 [animation-delay:-0.3s]" />
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-teal-600 [animation-delay:-0.15s]" />
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-teal-600" />
          </span>
          AI is searching documents...
        </div>
      </div>
    </div>
  );
}

export default function ChatPage() {
  const { user } = useAuth();
  const { sessionId, setSessionId, loadSessions, queuedPrompt, consumeQueuedPrompt } = useChat();
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState({});
  const bottomRef = useRef(null);
  const inputRef = useRef(null);
  const sendingRef = useRef(false);

  function resizeInput() {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }

  async function openSession(id) {
    setError("");
    try {
      const response = await api.get(`/chat/sessions/${id}/messages`);
      setMessages(response.data);
    } catch {
      setError("Could not load that chat.");
    }
  }

  useEffect(() => {
    if (!sessionId) {
      setMessages([]);
      setError("");
      inputRef.current?.focus();
      return;
    }
    openSession(sessionId);
  }, [sessionId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  useEffect(() => {
    resizeInput();
  }, [query]);

  async function sendMessage(text) {
    const trimmed = text.trim();
    if (!trimmed || busy || sendingRef.current) return;
    sendingRef.current = true;
    setError("");
    setQuery("");
    if (inputRef.current) inputRef.current.style.height = "auto";
    setBusy(true);
    setMessages((current) => [
      ...current,
      {
        id: `local-${Date.now()}`,
        role: "user",
        content: trimmed,
        citations: [],
      },
    ]);
    try {
      const response = await api.post("/chat", { query: trimmed, session_id: sessionId });
      const data = response.data;
      setSessionId(data.session_id);
      await openSession(data.session_id);
      await loadSessions();
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Chat failed.");
    } finally {
      sendingRef.current = false;
      setBusy(false);
      inputRef.current?.focus();
    }
  }

  function fillAndSend(text) {
    setQuery(text);
    sendMessage(text);
  }

  useEffect(() => {
    if (!queuedPrompt) return;
    const text = consumeQueuedPrompt();
    if (text) fillAndSend(text);
  }, [queuedPrompt]);

  function onAsk(event) {
    event.preventDefault();
    sendMessage(query);
  }

  function onKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage(query);
    }
  }

  function toggleFeedback(messageId, value) {
    setFeedback((current) => ({
      ...current,
      [messageId]: current[messageId] === value ? null : value,
    }));
  }

  const empty = messages.length === 0 && !busy;

  return (
    <section className="flex h-full min-h-0 flex-1 flex-col bg-slate-50 pt-12 md:pt-0">
      <div className="min-h-0 flex-1 overflow-y-auto">
        {empty ? (
          <EmptyState user={user} onHover={setQuery} onSelect={fillAndSend} />
        ) : (
          <div className="mx-auto w-full max-w-3xl space-y-6 px-4 py-6 md:py-8">
            {user.role === "ADMIN" && (
              <p className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-900">
                Admin is a system role. Employee knowledge answers stay with Super, Regional, and Normal users.
              </p>
            )}
            {messages.map((message) => {
              const usedSources = message.role === "assistant" ? sourcesUsedInAnswer(message) : [];
              if (message.role === "user") {
                return (
                  <div key={message.id} className="flex items-end justify-end gap-3">
                    <div className="max-w-[80%] rounded-2xl rounded-tr-sm bg-teal-800 px-4 py-3 text-sm text-white shadow-sm">
                      <p className="whitespace-pre-wrap">{message.content}</p>
                    </div>
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-teal-100 text-[#064e3b]">
                      <User className="h-4 w-4" />
                    </div>
                  </div>
                );
              }
              return (
                <div key={message.id} className="flex items-start gap-3">
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#064e3b] text-white">
                    <Bot className="h-4 w-4" />
                  </div>
                  <div className="max-w-[85%] rounded-2xl rounded-tl-sm border border-slate-200/80 bg-white px-5 py-4 text-slate-800 shadow-sm">
                    <AssistantMarkdown content={message.content} />
                    {usedSources.length > 0 && (
                      <div className="mt-4 flex flex-wrap gap-2">
                        {usedSources.map((item, index) => (
                          <a
                            key={`${item.document_id}-${item.citation_index ?? index}`}
                            href={item.source_url || "#"}
                            title={citationDetail(item)}
                            onClick={(event) => {
                              if (!item.source_url) {
                                event.preventDefault();
                                navigator.clipboard.writeText(citationLabel(item));
                              }
                            }}
                            className="inline-flex items-center gap-1.5 rounded-full border border-teal-200 bg-teal-50 px-3 py-1 text-xs font-medium text-teal-700 transition hover:border-teal-400 hover:bg-teal-100"
                            target={item.source_url ? "_blank" : undefined}
                            rel={item.source_url ? "noreferrer" : undefined}
                          >
                            <FileText className="h-3.5 w-3.5" />
                            {citationLabel(item)}
                          </a>
                        ))}
                      </div>
                    )}
                    <MessageActions
                      content={proseWithoutBibliography(message.content)}
                      messageId={message.id}
                      feedback={feedback[message.id]}
                      onFeedback={toggleFeedback}
                    />
                  </div>
                </div>
              );
            })}
            {busy && <TypingIndicator />}
            {error && <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      <div className="relative shrink-0 px-4 pb-5 pt-1">
        <div className="pointer-events-none absolute inset-x-0 -top-10 h-10 bg-gradient-to-t from-slate-50 to-transparent" />
        <form onSubmit={onAsk} className="mx-auto w-full max-w-3xl">
          <div className="flex items-end gap-2 rounded-2xl border border-slate-200/80 bg-white/75 p-2 shadow-lg shadow-slate-200/70 backdrop-blur">
            <textarea
              ref={inputRef}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={onKeyDown}
              rows={1}
              placeholder="Ask about approved SLT information…"
              className="max-h-40 min-h-11 flex-1 resize-none bg-transparent px-3 py-2.5 text-sm text-slate-800 outline-none placeholder:text-slate-400"
            />
            <button
              type="submit"
              disabled={busy || !query.trim()}
              className="rounded-xl bg-teal-700 p-2.5 text-white transition hover:bg-teal-800 disabled:cursor-not-allowed disabled:opacity-50"
              aria-label="Send message"
            >
              <ArrowUp className="h-4 w-4" />
            </button>
          </div>
          <p className="mt-2 text-center text-[11px] text-slate-400">Enter to send · Shift+Enter for a new line</p>
        </form>
      </div>
    </section>
  );
}
