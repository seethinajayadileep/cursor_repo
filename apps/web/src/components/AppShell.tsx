import { Link, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../state/auth";

const links = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/session/new", label: "New Session" },
  { to: "/sessions", label: "History" },
  { to: "/documents", label: "Documents" },
  { to: "/mock-interview", label: "Mock" },
  { to: "/settings", label: "Settings" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, demoMode, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded focus:bg-accent focus:px-3 focus:py-2 focus:text-ink">
        Skip to content
      </a>
      <header className="sticky top-0 z-40 border-b border-line/80 bg-ink/80 backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl items-center gap-4 px-4 py-3">
          <Link to="/dashboard" className="flex items-center gap-2" aria-label="InterviewPilot AI home">
            <LogoMark />
            <div>
              <div className="text-sm font-semibold tracking-tight">InterviewPilot AI</div>
              <div className="text-[11px] text-mist">Conversation copilot</div>
            </div>
          </Link>
          <nav className="ml-4 hidden items-center gap-1 md:flex" aria-label="Primary">
            {links.map((l) => (
              <NavLink
                key={l.to}
                to={l.to}
                className={({ isActive }) =>
                  `rounded-md px-3 py-1.5 text-sm ${isActive ? "bg-white/10 text-foam" : "text-mist hover:text-foam"}`
                }
              >
                {l.label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-2">
            {demoMode && (
              <span className="chip border-accent/40 text-accent" title="Running without paid API credentials">
                DEMO MODE
              </span>
            )}
            <span className="hidden text-sm text-mist sm:inline">{user?.name}</span>
            <button
              className="btn-ghost"
              onClick={async () => {
                await logout();
                navigate("/login");
              }}
            >
              Log out
            </button>
          </div>
        </div>
        <nav className="flex gap-1 overflow-x-auto border-t border-line/60 px-2 py-2 md:hidden" aria-label="Mobile">
          {links.map((l) => (
            <NavLink key={l.to} to={l.to} className="whitespace-nowrap rounded-md px-3 py-1 text-xs text-mist hover:bg-white/5">
              {l.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main id="main" className="mx-auto max-w-7xl px-4 py-6">
        {children}
      </main>
    </div>
  );
}

export function LogoMark({ className = "h-9 w-9" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 64 64" aria-hidden="true">
      <defs>
        <linearGradient id="ipg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#3DDC97" />
          <stop offset="100%" stopColor="#4C8DFF" />
        </linearGradient>
      </defs>
      <rect width="64" height="64" rx="16" fill="#121A2B" />
      <circle cx="32" cy="32" r="18" fill="none" stroke="url(#ipg)" strokeWidth="3" />
      <path d="M32 18 L36 32 L32 46 L28 32 Z" fill="url(#ipg)" />
      <circle cx="32" cy="32" r="3.5" fill="#E8EEF7" />
    </svg>
  );
}
