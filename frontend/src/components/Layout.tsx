import { NavLink, Outlet } from "react-router-dom";
import DisclaimerBanner from "./DisclaimerBanner";

const navItems = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/watchlist", label: "Watchlist" },
  { to: "/settings", label: "Settings" },
];

export default function Layout() {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between gap-4 flex-wrap">
          <div className="font-bold text-lg tracking-tight">📈 Stock Signal Engine</div>
          <nav className="flex gap-1">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  `px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                    isActive ? "bg-slate-800 text-white" : "text-slate-400 hover:text-white hover:bg-slate-900"
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      <main className="flex-1 max-w-6xl w-full mx-auto px-4 py-6 space-y-4">
        <DisclaimerBanner />
        <Outlet />
      </main>
      <footer className="text-center text-xs text-slate-600 py-4">
        Stock Signal Engine — analytical tool, not financial advice.
      </footer>
    </div>
  );
}
