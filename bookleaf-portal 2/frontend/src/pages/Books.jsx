import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { inr } from "../constants";

export default function Books() {
  const [books, setBooks] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => { api("/books").then(setBooks).catch((e) => setError(e.message)); }, []);

  if (error) return <p className="error">{error}</p>;
  if (!books) return <p className="muted">Loading your books…</p>;
  if (books.length === 0) return <div className="card"><p>No books on your account yet.</p></div>;

  return (
    <>
      <h2>My Books</h2>
      <div className="scroll">
        <table>
          <thead>
            <tr><th>Title</th><th>ISBN</th><th>Genre</th><th>Published</th><th>Status</th><th>MRP</th>
              <th>Copies sold</th><th>Royalty earned</th><th>Paid</th><th>Pending</th><th /></tr>
          </thead>
          <tbody>
            {books.map((b) => {
              const live = b.copies_sold > 0 || b.royalty_earned > 0;
              return (
                <tr key={b.id}>
                  <td>{b.title}</td>
                  {/* Books still in production have no ISBN/date/sales yet: show that honestly instead of blanks. */}
                  <td>{b.isbn || <span className="muted">Not assigned yet</span>}</td>
                  <td>{b.genre || "—"}</td>
                  <td>{b.publication_date || <span className="muted">Not published</span>}</td>
                  <td><span className="chip">{b.status || "—"}</span></td>
                  <td>{b.mrp == null ? <span className="muted">—</span> : inr(b.mrp)}</td>
                  <td>{b.copies_sold}</td>
                  <td>{live ? inr(b.royalty_earned) : <span className="muted">No sales yet</span>}</td>
                  <td>{inr(b.royalty_paid)}</td>
                  <td className={b.royalty_pending > 0 ? "warn" : ""}>{inr(b.royalty_pending)}</td>
                  <td><Link to="/tickets/new" state={{ bookId: b.id }}>Raise query</Link></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="muted small">Royalties are calculated quarterly and paid within 45 days of quarter end (minimum payout ₹1,000; smaller balances roll over).</p>
    </>
  );
}
