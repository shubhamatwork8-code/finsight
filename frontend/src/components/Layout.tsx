import { useState } from "react";
import { Menu } from "lucide-react";
import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";

export function Layout() {
  const [open, setOpen] = useState(false);
  return (
    <div className="min-h-screen bg-ink">
      <Sidebar open={open} onClose={() => setOpen(false)} />
      <div className="lg:pl-60">
        <div className="flex items-center gap-3 border-b border-line px-4 py-3 lg:hidden">
          <button onClick={() => setOpen(true)} aria-label="Open navigation" className="rounded-md border border-line p-2">
            <Menu size={16} />
          </button>
          <span className="text-sm font-medium">FinSight</span>
        </div>
        <main className="px-4 py-6 md:px-8 md:py-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
