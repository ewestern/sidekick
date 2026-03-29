import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { getUserEmail } from "../lib/auth";
import { ToastContainer } from "./ui/Toast";

const navItems = [
  { to: "/sources", label: "Sources" },
  { to: "/assignments", label: "Assignments" },
  { to: "/agent-configs", label: "Agent Configs" },
  { to: "/artifacts", label: "Artifacts" },
  { to: "/api-clients", label: "API Clients" },
];

export function AppShell() {
  const navigate = useNavigate();
  const email = getUserEmail();

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-top">
          <h1>Sidekick</h1>
          <p>Newsroom admin</p>
        </div>

        <nav className="sidebar-nav">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                isActive ? "nav-link active" : "nav-link"
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-footer">
          <p className="user-email">{email ?? "Signed in"}</p>
          <button
            className="danger-outline"
            onClick={() => navigate("/logout")}
          >
            Sign out
          </button>
        </div>
      </aside>

      <section className="main-content">
        <Outlet />
      </section>

      <ToastContainer />
    </div>
  );
}
