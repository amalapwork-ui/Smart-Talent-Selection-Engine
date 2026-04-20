import React, { useState, useEffect } from "react";
import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";

export default function Layout() {
  // Desktop: open by default; mobile: closed by default
  const [sidebarOpen, setSidebarOpen] = useState(window.innerWidth >= 768);

  // Close sidebar on mobile when window resizes down
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth < 768) setSidebarOpen(false);
    };
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  const isMobile = () => window.innerWidth < 768;

  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden">
      <Sidebar
        open={sidebarOpen}
        onToggle={() => setSidebarOpen((v) => !v)}
        onClose={() => { if (isMobile()) setSidebarOpen(false); }}
      />

      {/* Main content — shifts right on desktop when sidebar is open */}
      <main
        className={`flex-1 overflow-y-auto transition-all duration-300
          ${sidebarOpen ? "md:ml-64" : "md:ml-16"} ml-0`}
      >
        {/* Mobile top bar */}
        <div className="md:hidden flex items-center gap-3 px-4 py-3 bg-white border-b border-gray-200 sticky top-0 z-20">
          <button
            onClick={() => setSidebarOpen((v) => !v)}
            className="p-2 rounded-lg text-gray-500 hover:bg-gray-100"
            aria-label="Open menu"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 bg-blue-600 rounded-lg flex items-center justify-center text-white font-bold text-xs">ST</div>
            <span className="font-semibold text-gray-900 text-sm">Smart Talent</span>
          </div>
        </div>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
