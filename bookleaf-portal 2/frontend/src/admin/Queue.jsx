import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { CATEGORIES, PRIORITIES, STATUSES, age } from "../constants";
import { usePolling } from "../hooks/usePolling";

export default function Queue() {
  const nav = useNavigate();
  const [f, setF] = useState({ status: "", category: "", priority: "", assigned: "", date_from: "", date_to: "" });
  const [tickets, setTickets] = useState(null);
  const [error, setError] = useState("");

  const qs = new URLSearchParams(Object.entries(f).filter(([, v]) => v)).toString();
  usePolling(() => api(`/admin/tickets?${qs}`).then((d) => { setTickets(d); setError(""); }).catch((e) => setError(e.message)), 5000, [qs]);

  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const Select = ({ k, label, options }) => (
    <select value={f[k]} onChange={set(k)}><option value="">{label}</option>{options.map((o) => <option key={o}>{o}</option>)}</select>
  );

  return (
    <>
      <h2>Ticket Queue</h2>
      <div className="filters">
        <Select k="status" label="All statuses" options={STATUSES} />
        <Select k="category" label="All categories" options={CATEGORIES} />
        <Select k="priority" label="All priorities" options={PRIORITIES} />
        <select value={f.assigned} onChange={set("assigned")}>
          <option value="">Anyone</option><option value="me">Assigned to me</option><option value="unassigned">Unassigned</option>
        </select>
        <input type="date" value={f.date_from} onChange={set("date_from")} title="From" />
        <input type="date" value={f.date_to} onChange={set("date_to")} title="To" />
      </div>
      {error && <p className="error">{error}</p>}
      {!tickets ? <p className="muted">Loading…</p> : tickets.length === 0 ? <div className="card"><p>No tickets match these filters.</p></div> : (
        <div className="scroll">
          <table className="clickable">
            <thead><tr><th>Priority</th><th>#</th><th>Subject</th><th>Author</th><th>Category</th><th>Status</th><th>Assignee</th><th>Age</th></tr></thead>
            <tbody>
              {tickets.map((t) => {
                const unresolved = !["Resolved", "Closed"].includes(t.status);
                const stale = unresolved && Date.now() - new Date(t.created_at) > 48 * 36e5;
                return (
                  <tr key={t.id} onClick={() => nav(`/admin/tickets/${t.id}`)}>
                    <td><span className={`chip p-${t.priority}`}>{t.priority}</span>{t.priority_overridden && <span title="Overridden by admin"> ✎</span>}</td>
                    <td>{t.id}</td>
                    <td>{t.subject}{t.ai_status === "failed" && <span className="chip warnchip" title="AI classification failed; keyword fallback used"> AI offline</span>}</td>
                    <td>{t.author.name}</td>
                    <td>{t.category}{t.category_overridden && <span title="Overridden by admin"> ✎</span>}</td>
                    <td><span className={`chip s-${t.status.replace(" ", "")}`}>{t.status}</span></td>
                    <td>{t.assigned_to?.name || <span className="muted">Unassigned</span>}</td>
                    <td className={stale ? "warn" : ""}>{age(t.created_at)}{stale && " ⚠"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
