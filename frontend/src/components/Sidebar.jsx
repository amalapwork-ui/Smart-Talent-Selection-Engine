import React from "react";
import { NavLink } from "react-router-dom";

const NAV_ITEMS = [
  { to: "/dashboard", icon: "📊", label: "Dashboard" },
  { to: "/upload",    icon: "📤", label: "Upload Resumes" },
  { to: "/jobs",      icon: "💼", label: "Jobs" },
  { to: "/rankings",  icon: "🏆", label: "Rankings" },
];

export default function Sidebar({ open, onToggle, onClose }) {
  return (
    <>
      {/* Mobile overlay — tapping it closes the sidebar */}
      {open && (
        <div
          className="fixed inset-0 bg-black/30 z-30 md:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={`fixed top-0 left-0 h-full bg-white border-r border-gray-200 z-40
          transition-all duration-300 flex flex-col
          ${open ? "w-64" : "w-0 md:w-16 overflow-hidden"}`}
      >
        {/* Brand */}
        <div className="flex items-center gap-3 px-4 py-5 border-b border-gray-100 min-w-0">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-white font-bold text-sm flex-shrink-0">
            ST
          </div>
          {open && (
            <div className="overflow-hidden">
              <p className="font-bold text-gray-900 text-sm leading-tight whitespace-nowrap">Smart Talent</p>
              <p className="text-xs text-gray-500 whitespace-nowrap">Selection Engine</p>
            </div>
          )}
        </div>

        {/* Nav */}
        <nav className="flex-1 py-4 space-y-1 px-2 overflow-y-auto">
          {NAV_ITEMS.map(({ to, icon, label }) => (
            <NavLink
              key={to}
              to={to}
              onClick={onClose}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors
                 ${isActive
                   ? "bg-blue-50 text-blue-700"
                   : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"}`
              }
            >
              <span className="text-base flex-shrink-0">{icon}</span>
              {open && <span className="truncate">{label}</span>}
            </NavLink>
          ))}
        </nav>

        {/* Toggle (desktop only) */}
        <button
          onClick={onToggle}
          className="hidden md:flex p-4 border-t border-gray-100 text-gray-400 hover:text-gray-700 text-xs items-center gap-2"
        >
          <span>{open ? "◀" : "▶"}</span>
          {open && <span>Collapse</span>}
        </button>
      </aside>
    </>
  );
}
