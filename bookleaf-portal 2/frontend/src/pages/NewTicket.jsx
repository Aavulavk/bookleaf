import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { api } from "../api";

export default function NewTicket() {
  const nav = useNavigate();
  const { state } = useLocation();
  const [books, setBooks] = useState([]);
  const [bookId, setBookId] = useState(state?.bookId ?? "");
  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const [fileName, setFileName] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => { api("/books").then(setBooks).catch(() => {}); }, []);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api("/tickets", { method: "POST", body: { book_id: bookId === "" ? null : Number(bookId), subject, description } });
      nav("/tickets");
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  };

  return (
    <form className="card narrow" onSubmit={submit}>
      <h2>Submit a Support Query</h2>
      <label>Which book is this about?
        <select value={bookId} onChange={(e) => setBookId(e.target.value)}>
          <option value="">General / Account Level</option>
          {books.map((b) => <option key={b.id} value={b.id}>{b.title}</option>)}
        </select>
      </label>
      <label>Subject<input value={subject} onChange={(e) => setSubject(e.target.value)} minLength={3} maxLength={200} required /></label>
      <label>Describe your issue
        <textarea rows={7} value={description} onChange={(e) => setDescription(e.target.value)} minLength={10} maxLength={5000} required
          placeholder="Include what you expected, what happened, and any dates or amounts." />
      </label>
      <label>Attachment (optional)
        <input type="file" onChange={(e) => setFileName(e.target.files[0]?.name || "")} />
        {fileName && <span className="muted small">UI preview only: file uploads are not enabled yet, so please mention “{fileName}” in your description.</span>}
      </label>
      {error && <p className="error">{error}</p>}
      <button disabled={busy}>{busy ? "Submitting…" : "Submit query"}</button>
    </form>
  );
}
