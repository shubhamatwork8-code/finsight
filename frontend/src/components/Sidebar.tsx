import { NavLink, useNavigate } from "react-router-dom";
import {
  ArrowLeftRight,
  BarChart3,
  LayoutDashboard,
  LogOut,
  ScrollText,
  Settings,
  ShieldAlert,
  Wallet,
  X,
} from "lucide-react";
import { useAuth } from "./Auth";

const links = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/accounts", label: "Accounts", icon: Wallet },
  { to: "/transactions", label: "Transactions", icon: ArrowLeftRight },
  { to: "/fraud-alerts", label: "Fraud Alerts", icon: ShieldAlert },
  { to: "/analytics", label: "Analytics", icon: BarChart3 },
  { to: "/audit-log", label: "Audit Log", icon: ScrollText },
];

export function Sidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  return (
    <>
      {open ? <button className="fixed inset-0 z-30 bg-black/50 lg:hidden" aria-label="Close menu" onClick={onClose} /> : null}
      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-60 flex-col border-r border-line bg-navy px-3 py-5 transition-transform lg:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="mb-8 flex items-start justify-between px-2">
          <div>
            <div className="flex items-center gap-2">
              <span className="grid h-8 w-8 place-items-center rounded-md bg-emerald font-mono text-xs font-medium text-ink">FS</span>
              <div>
                <p className="text-base font-semibold leading-none text-white">FinSight</p>
                <p className="mt-1 text-[10px] uppercase tracking-[0.16em] text-muted">Enterprise Risk Engine</p>
              </div>
            </div>
          </div>
          <button className="text-muted lg:hidden" onClick={onClose} aria-label="Close sidebar">
            <X size={18} />
          </button>
        </div>
        <nav className="flex flex-1 flex-col gap-1">
          {links.map((link) => {
            const Icon = link.icon;
            return (
              <NavLink
                key={link.to}
                to={link.to}
                onClick={onClose}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-md px-3 py-2 text-sm ${
                    isActive ? "bg-panel2 text-white" : "text-muted hover:bg-panel hover:text-white"
                  }`
                }
              >
                <Icon size={16} />
                {link.label}
              </NavLink>
            );
          })}
        </nav>
        <NavLink
          to="/settings"
          onClick={onClose}
          className={({ isActive }) =>
            `mt-4 flex items-center gap-3 rounded-md px-3 py-2 text-sm ${
              isActive ? "bg-panel2 text-white" : "text-muted hover:bg-panel hover:text-white"
            }`
          }
        >
          <Settings size={16} />
          Settings
        </NavLink>
        <button
          onClick={() => {
            signOut();
            onClose();
            navigate("/login");
          }}
          className="mt-2 flex w-full items-center gap-3 rounded-md px-3 py-2 text-left text-sm text-muted hover:bg-panel hover:text-white"
        >
          <LogOut size={16} />
          <span>
            <span className="block text-white">{user?.full_name ?? "Sign out"}</span>
            <span className="block text-xs text-muted">Sign out</span>
          </span>
        </button>
      </aside>
    </>
  );
}
