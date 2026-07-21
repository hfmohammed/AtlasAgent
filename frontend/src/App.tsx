import { FormEvent, useEffect, useMemo, useState } from "react";
import { ArrowUp, Bot, Database, FileSearch, Plus, ShieldCheck, Sparkles, User } from "lucide-react";
import { approveAction, getSystemStats, sendMessage } from "./api";
import type { SystemStats } from "./api";
import { SourcePanel } from "./components/SourcePanel";
import type { ChatResponse, Message } from "./types";

const suggestions = [
  "What is our enterprise refund policy?",
  "Show me order ORD-2048",
  "Create a support draft for CUST-1001",
];

export default function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [query, setQuery] = useState("");
  const [conversationId, setConversationId] = useState<string>();
  const [activeResponse, setActiveResponse] = useState<ChatResponse>();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>();
  const [stats, setStats] = useState<SystemStats>();

  useEffect(() => {
    getSystemStats().then(setStats).catch(() => undefined);
  }, []);

  const date = useMemo(
    () => new Intl.DateTimeFormat("en", { month: "short", day: "numeric" }).format(new Date()),
    [],
  );

  async function submit(event?: FormEvent, suggested?: string) {
    event?.preventDefault();
    const content = (suggested ?? query).trim();
    if (!content || loading) return;
    setMessages((current) => [...current, { id: crypto.randomUUID(), role: "user", body: content }]);
    setQuery("");
    setLoading(true);
    setError(undefined);
    try {
      const response = await sendMessage(content, conversationId);
      setConversationId(response.conversation_id);
      setActiveResponse(response);
      getSystemStats().then(setStats).catch(() => undefined);
      setMessages((current) => [
        ...current,
        { id: crypto.randomUUID(), role: "assistant", body: response.answer, response },
      ]);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  async function approve(actionId: string, token: string) {
    const result = await approveAction(actionId, token);
    setActiveResponse((current) => current && ({
      ...current,
      tool_calls: current.tool_calls.map((call) =>
        call.action_id === actionId
          ? { ...call, status: "completed", result: result.result }
          : call,
      ),
    }));
    getSystemStats().then(setStats).catch(() => undefined);
  }

  return (
    <main className="shell">
      <nav className="sidebar">
        <div className="brand"><div className="brand-mark"><Sparkles size={18} /></div><span>AtlasAgent</span></div>
        <button className="new-chat" onClick={() => { setMessages([]); setConversationId(undefined); setActiveResponse(undefined); }}>
          <Plus size={17} /> New conversation
        </button>
        <div className="nav-label">Workspace</div>
        <div className="nav-item active"><Bot size={17} /> Agent</div>
        <div className="nav-item"><Database size={17} /> Knowledge base <span>{stats?.documents ?? "—"}</span></div>
        <div className="nav-item"><FileSearch size={17} /> Evaluations</div>
        <div className="nav-item"><ShieldCheck size={17} /> Audit log</div>
        <div className="environment"><span></span><div><strong>System ready</strong><small>{stats?.chunks ?? 0} indexed chunks</small></div></div>
      </nav>

      <section className="workspace">
        <header><div><span>Support workspace</span><small>{date}</small></div><button className="avatar">HM</button></header>
        <div className="conversation">
          {messages.length === 0 ? (
            <div className="welcome">
              <div className="welcome-mark"><Sparkles size={28} /></div>
              <p className="eyebrow">Enterprise intelligence</p>
              <h1>What can I help you find?</h1>
              <p className="lede">Ask about company knowledge, inspect business records, or prepare a safe workflow action.</p>
              <div className="suggestions">
                {suggestions.map((suggestion) => <button key={suggestion} onClick={() => submit(undefined, suggestion)}>{suggestion}<ArrowUp size={15} /></button>)}
              </div>
            </div>
          ) : (
            <div className="thread">
              {messages.map((message) => (
                <article className={`message ${message.role}`} key={message.id} onClick={() => message.response && setActiveResponse(message.response)}>
                  <div className="message-avatar">{message.role === "user" ? <User size={17} /> : <Sparkles size={17} />}</div>
                  <div><strong>{message.role === "user" ? "You" : "AtlasAgent"}</strong><p>{message.body}</p>
                    {message.response && message.response.citations.length > 0 && <button className="source-count">{message.response.citations.length} cited sources</button>}
                  </div>
                </article>
              ))}
              {loading && <article className="message assistant"><div className="message-avatar"><Sparkles size={17} /></div><div className="thinking"><i></i><i></i><i></i></div></article>}
            </div>
          )}
          {error && <div className="error">{error}</div>}
          <form className="composer" onSubmit={submit}>
            <textarea value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); submit(); } }} placeholder="Ask AtlasAgent…" rows={1} />
            <div><span>Hybrid retrieval · 5 sources</span><button aria-label="Send" disabled={loading || !query.trim()}><ArrowUp size={18} /></button></div>
          </form>
        </div>
      </section>
      <SourcePanel response={activeResponse} onApprove={approve} />
    </main>
  );
}

