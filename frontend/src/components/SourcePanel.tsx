import { useState } from "react";
import { BookOpen, CheckCircle2, Clock3, KeyRound, Wrench } from "lucide-react";
import type { ChatResponse } from "../types";

type Props = {
  response?: ChatResponse;
  onApprove: (actionId: string, token: string) => Promise<void>;
};

export function SourcePanel({ response, onApprove }: Props) {
  const [token, setToken] = useState("");
  const [approving, setApproving] = useState<string>();
  const [approvalError, setApprovalError] = useState<string>();

  async function submitApproval(actionId: string) {
    setApproving(actionId);
    setApprovalError(undefined);
    try {
      await onApprove(actionId, token);
      setToken("");
    } catch (error) {
      setApprovalError(error instanceof Error ? error.message : "Approval failed");
    } finally {
      setApproving(undefined);
    }
  }

  return (
    <aside className="inspector">
      <div className="inspector-heading">
        <span>Run inspector</span>
        <span className="live-dot">Live</span>
      </div>
      {!response ? (
        <div className="empty-inspector">
          <div className="empty-icon"><BookOpen size={20} /></div>
          <p>Ask a question to inspect evidence and tool activity.</p>
        </div>
      ) : (
        <>
          <div className="metrics">
            <div><Clock3 size={15} /><span>{response.latency_ms.toFixed(0)} ms</span></div>
            <div><BookOpen size={15} /><span>{response.citations.length} sources</span></div>
            <div><Wrench size={15} /><span>{response.tool_calls.length} tools</span></div>
          </div>
          <section className="inspect-section">
            <h3>Evidence</h3>
            {response.citations.length === 0 && <p className="muted">No source matched.</p>}
            {response.citations.map((citation, index) => (
              <article className="source-card" key={citation.chunk_id}>
                <div className="source-meta">
                  <span className="source-index">{index + 1}</span>
                  <strong>{citation.document_name}</strong>
                  <span>{Math.round(citation.score * 100)}%</span>
                </div>
                <p>{citation.excerpt}</p>
              </article>
            ))}
          </section>
          <section className="inspect-section">
            <h3>Tool activity</h3>
            {response.tool_calls.length === 0 && <p className="muted">No tools called.</p>}
            {response.tool_calls.map((call) => (
              <article className="tool-card" key={`${call.name}-${call.action_id ?? "done"}`}>
                <CheckCircle2 size={16} />
                <div><strong>{call.name}</strong><span>{call.status.replace("_", " ")}</span></div>
                {call.status === "approval_required" && call.action_id && (
                  <div className="approval-box">
                    <label><KeyRound size={13} /> Approval token</label>
                    <input
                      type="password"
                      value={token}
                      onChange={(event) => setToken(event.target.value)}
                      placeholder="Paste signed token"
                    />
                    <button
                      disabled={!token || approving === call.action_id}
                      onClick={() => submitApproval(call.action_id!)}
                    >
                      {approving === call.action_id ? "Executing…" : "Approve & execute"}
                    </button>
                  </div>
                )}
              </article>
            ))}
            {approvalError && <p className="approval-error">{approvalError}</p>}
          </section>
        </>
      )}
    </aside>
  );
}

