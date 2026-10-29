import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { fmtDate } from "../constants";
import { usePolling } from "../hooks/usePolling";

function Ticket({ t }) {
  const [open, setOpen] = useState(false);
  const replies = t.messages.length;
  return (
    <div className="card">
      <div className="row" onClick={() => setOpen(!open)} style={{ cursor: "pointer" }}>
        <div className="grow">
          <strong>#{t.id} {t.subject}</strong>
          <div className="muted small">{t.book_title || "General / Account Level"} · {t.category} · {fmtDate(t.created_at)}</div>
        </div>
        {replies > 0 && <span className="chip blue">{replies} repl{replies > 1 ? "ies" : "y"}</span>}
        <span className={`chip s-${t.status.replace(" ", "")}`}>{t.status}</span>
      </div>
      {open && (
        <div className="thread">
          <div className="msg author"><div className="muted small">You · {fmtDate(t.created_at)}</div>{t.description}</div>
          {t.messages.map((m) => (
            <div key={m.id} className="msg admin"><div className="muted small">BookLeaf Support · {fmtDate(m.created_at)}</div>{m.body}</div>
          ))}
          {replies === 0 && <p className="muted small">No response yet. Our team will get back to you soon, and this page updates automatically.</p>}
        </div>
      )}
    </div>
  );
}

export default function MyTickets() {
  const [tickets, setTickets] = useState(null);
  const [error, setError] = useState("");

  // Near-real-time: replies appear within a few seconds, no manual refresh.
  usePolling(() => api("/tickets").then((d) => { setTickets(d); setError(""); }).catch((e) => setError(e.message)), 5000);

  if (!tickets) return error ? <p className="error">{error}</p> : <p className="muted">Loading your tickets…</p>;
  return (
    <>
      <div className="row"><h2 className="grow">My Tickets</h2><Link to="/tickets/new">+ New query</Link></div>
      {error && <p className="error small">{error} (retrying…)</p>}
      {tickets.length === 0
        ? <div className="card"><p>You haven’t raised any queries yet. <Link to="/tickets/new">Submit one</Link>.</p></div>
        : tickets.map((t) => <Ticket key={t.id} t={t} />)}
    </>
  );
}
