import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { CATEGORIES, PRIORITIES, STATUSES, fmtDate, inr } from "../constants";
import { usePolling } from "../hooks/usePolling";

export default function TicketDetail() {
  const { id } = useParams();
  const [t, setT] = useState(null);
  const [ctx, setCtx] = useState(null);
  const [error, setError] = useState("");

  const [draft, setDraft] = useState("");
  const [draftState, setDraftState] = useState("loading"); // loading | ready | unavailable
  const [draftMsg, setDraftMsg] = useState("");
  const [sendStatus, setSendStatus] = useState("");
  const [sending, setSending] = useState(false);
  const [note, setNote] = useState("");

  // Poll only the ticket (thread/status); the draft box is separate state so polling never wipes admin edits.
  usePolling(() => api(`/admin/tickets/${id}`).then(setT).catch((e) => setError(e.message)), 6000, [id]);
  useEffect(() => { api(`/admin/tickets/${id}/context`).then(setCtx).catch(() => {}); }, [id]);

  const loadDraft = async (regenerate = false) => {
    setDraftState("loading");
    try {
      const d = await api(`/admin/tickets/${id}/draft${regenerate ? "?regenerate=true" : ""}`, { method: "POST" });
      setDraft(d.draft);
      setDraftState("ready");
    } catch (e) {
      setDraftState("unavailable");
      setDraftMsg(e.code === "AI_UNAVAILABLE" ? e.message : `Could not generate a draft: ${e.message}`);
    }
  };
  useEffect(() => { loadDraft(false); }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  const patch = (body) => api(`/admin/tickets/${id}`, { method: "PATCH", body }).then(setT).catch((e) => setError(e.message));

  const send = async () => {
    setSending(true);
    setError("");
    try {
      setT(await api(`/admin/tickets/${id}/reply`, { method: "POST", body: { body: draft, status: sendStatus || null } }));
      setDraft("");
      setDraftState("unavailable");
      setDraftMsg("Reply sent. Write another reply below if needed.");
    } catch (e) { setError(e.message); }
    setSending(false);
  };

  const addNote = async () => {
    try { setT(await api(`/admin/tickets/${id}/notes`, { method: "POST", body: { body: note } })); setNote(""); }
    catch (e) { setError(e.message); }
  };

  const retryAi = () => api(`/admin/tickets/${id}/reclassify`, { method: "POST" }).then(setT).catch((e) => setError(e.message));

  if (!t) return error ? <p className="error">{error}</p> : <p className="muted">Loading…</p>;
  const publicMsgs = t.messages.filter((m) => !m.is_internal);
  const notes = t.messages.filter((m) => m.is_internal);

  return (
    <>
      <p><Link to="/admin">← Back to queue</Link></p>
      <div className="row"><h2 className="grow">#{t.id} {t.subject}</h2><span className={`chip s-${t.status.replace(" ", "")}`}>{t.status}</span></div>
      {error && <p className="error">{error}</p>}

      <div className="grid2">
        <section>
          <div className="card">
            <div className="thread">
              <div className="msg author"><div className="muted small">{t.author.name} · {fmtDate(t.created_at)}</div>{t.description}</div>
              {publicMsgs.map((m) => <div key={m.id} className="msg admin"><div className="muted small">BookLeaf Support · {fmtDate(m.created_at)}</div>{m.body}</div>)}
            </div>
          </div>

          <div className="card">
            <div className="row">
              <h3 className="grow">Reply to author</h3>
              <button className="ghost" onClick={() => loadDraft(true)} disabled={draftState === "loading"}>↻ Regenerate AI draft</button>
            </div>
            {draftState === "loading" && <p className="muted small">AI is drafting a reply from the knowledge base…</p>}
            {draftState === "unavailable" && <p className="notice">{draftMsg}</p>}
            {draftState === "ready" && <p className="muted small">AI-generated draft. Review and edit before sending; check it against the account facts on the right.</p>}
            <textarea rows={11} value={draft} onChange={(e) => setDraft(e.target.value)} placeholder="Write your reply to the author…" />
            <div className="row">
              <label className="inline">After sending, set status:
                <select value={sendStatus} onChange={(e) => setSendStatus(e.target.value)}>
                  <option value="">Automatic (Open → In Progress)</option>{STATUSES.map((s) => <option key={s}>{s}</option>)}
                </select>
              </label>
              <span className="grow" />
              <button onClick={send} disabled={sending || !draft.trim()}>{sending ? "Sending…" : "Send reply"}</button>
            </div>
          </div>
        </section>

        <aside>
          <div className="card">
            <h3>Triage</h3>
            <label>Status
              <select value={t.status} onChange={(e) => patch({ status: e.target.value })}>{STATUSES.map((s) => <option key={s}>{s}</option>)}</select>
            </label>
            <label>Category {t.category_overridden && <span className="chip warnchip">overridden · AI said {t.ai_category}</span>}
              <select value={t.category} onChange={(e) => patch({ category: e.target.value })}>{CATEGORIES.map((c) => <option key={c}>{c}</option>)}</select>
            </label>
            <label>Priority {t.priority_overridden && <span className="chip warnchip">overridden · AI said {t.ai_priority}</span>}
              <select value={t.priority} onChange={(e) => patch({ priority: e.target.value })}>{PRIORITIES.map((p) => <option key={p}>{p}</option>)}</select>
            </label>
            {t.ai_status === "done" && <p className="muted small">AI reasoning: {t.ai_reason}</p>}
            {t.ai_status === "pending" && <p className="muted small">AI is classifying this ticket…</p>}
            {t.ai_status === "failed" && <p className="notice">AI classification unavailable; a keyword fallback was used. <button className="ghost" onClick={retryAi}>Retry AI</button></p>}
            <p>Assigned to: <strong>{t.assigned_to?.name || "Nobody"}</strong>{" "}
              <button className="ghost" onClick={() => patch({ assignee: "me" })}>Assign to me</button></p>
          </div>

          <div className="card">
            <h3>Author &amp; book</h3>
            <p>{t.author.name}<br /><span className="muted small">{t.author.email}</span></p>
            <p className="small">Bank details linked: <strong>{ctx ? (ctx.bank_linked == null ? "Unknown" : ctx.bank_linked ? "Yes" : "No") : "…"}</strong></p>
            {t.book_id == null ? <p className="muted small">General / Account Level query</p> : ctx?.book && (
              <dl className="facts">
                <dt>Book</dt><dd>{ctx.book.title}</dd>
                <dt>Status</dt><dd>{ctx.book.status || "—"}</dd>
                <dt>ISBN</dt><dd>{ctx.book.isbn || "Not assigned"}</dd>
                <dt>Copies sold</dt><dd>{ctx.book.copies_sold}</dd>
                <dt>Earned</dt><dd>{inr(ctx.book.royalty_earned)}</dd>
                <dt>Paid</dt><dd>{inr(ctx.book.royalty_paid)}</dd>
                <dt>Pending</dt><dd>{inr(ctx.book.royalty_pending)}</dd>
              </dl>
            )}
          </div>

          <div className="card">
            <h3>Internal notes <span className="muted small">(never shown to the author)</span></h3>
            {notes.map((n) => <div key={n.id} className="msg note"><div className="muted small">{fmtDate(n.created_at)}</div>{n.body}</div>)}
            <textarea rows={3} value={note} onChange={(e) => setNote(e.target.value)} placeholder="Add a private note…" />
            <button className="ghost" onClick={addNote} disabled={!note.trim()}>Add note</button>
          </div>
        </aside>
      </div>
    </>
  );
}
