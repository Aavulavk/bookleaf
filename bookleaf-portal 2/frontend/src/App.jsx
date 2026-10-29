import { Navigate, NavLink, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth";
import Login from "./pages/Login";
import Books from "./pages/Books";
import NewTicket from "./pages/NewTicket";
import MyTickets from "./pages/MyTickets";
import Queue from "./admin/Queue";
import TicketDetail from "./admin/TicketDetail";

function Guard({ role, children }) {
  const { user, loading } = useAuth();
  if (loading) return <p className="muted pad">Loading…</p>;
  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== role) return <Navigate to={user.role === "admin" ? "/admin" : "/books"} replace />;
  return children;
}

function Nav() {
  const { user, logout } = useAuth();
  if (!user) return null;
  const links = user.role === "admin"
    ? [["/admin", "Ticket Queue"]]
    : [["/books", "My Books"], ["/tickets/new", "Submit a Query"], ["/tickets", "My Tickets"]];
  return (
    <header className="nav">
      <strong>BookLeaf {user.role === "admin" ? "Admin" : "Author Portal"}</strong>
      <nav>{links.map(([to, label]) => <NavLink key={to} to={to} end>{label}</NavLink>)}</nav>
      <span className="grow" />
      <span className="muted">{user.name}</span>
      <button className="ghost" onClick={logout}>Log out</button>
    </header>
  );
}

export default function App() {
  const { user } = useAuth();
  return (
    <>
      <Nav />
      <main className="container">
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/books" element={<Guard role="author"><Books /></Guard>} />
          <Route path="/tickets/new" element={<Guard role="author"><NewTicket /></Guard>} />
          <Route path="/tickets" element={<Guard role="author"><MyTickets /></Guard>} />
          <Route path="/admin" element={<Guard role="admin"><Queue /></Guard>} />
          <Route path="/admin/tickets/:id" element={<Guard role="admin"><TicketDetail /></Guard>} />
          <Route path="*" element={<Navigate to={user ? (user.role === "admin" ? "/admin" : "/books") : "/login"} replace />} />
        </Routes>
      </main>
    </>
  );
}
