import React, { useMemo, useState } from "react";
import { Link, NavLink } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { FiChevronDown, FiLogOut, FiMenu, FiShield, FiUser, FiX } from "react-icons/fi";

import { useAuth } from "../../contexts/AuthContext";

function NavItems({ items, onNavigate }) {
  return items.map((item) => (
    <NavLink
      key={item.to}
      to={item.to}
      onClick={onNavigate}
      className={({ isActive }) =>
        `rounded-lg px-3 py-2 text-sm font-medium transition ${
          isActive
            ? "bg-white/15 text-white"
            : "text-white/70 hover:bg-white/10 hover:text-white"
        }`
      }
    >
      {item.label}
    </NavLink>
  ));
}

function Navbar() {
  const { user, logout, hasRole } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);

  const links = useMemo(() => {
    if (hasRole("admin")) {
      return [
        { to: "/admin/dashboard", label: "Dashboard" },
        { to: "/admin/claims",    label: "Claims" },
        { to: "/admin/reports",   label: "Reports" },
        { to: "/admin/surveyors", label: "Surveyors" },
        { to: "/admin/logs",      label: "Logs" },
        { to: "/admin/ml-models", label: "ML Models" },
      ];
    }
    return [
      { to: "/dashboard", label: "Dashboard" },
      { to: "/claims",    label: "Claims" },
      { to: "/reports",   label: "Reports" },
    ];
  }, [hasRole]);

  const handleLogout = async () => {
    await logout();
    setProfileOpen(false);
    setMobileOpen(false);
  };

  return (
    <header className="sticky top-0 z-40 bg-navy-900 shadow-nav">
      {/* Subtle gradient accent line at bottom */}
      <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-navy-500/60 to-transparent" />

      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
        {/* Logo */}
        <Link
          className="flex items-center gap-2.5 text-white"
          to="/dashboard"
        >
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-white/15 text-white">
            <FiShield size={16} />
          </span>
          <span className="text-base font-bold tracking-tight">
            AutoFraud<span className="text-navy-300 font-normal"> Intelligence</span>
          </span>
        </Link>

        {/* Desktop nav links */}
        <nav className="hidden items-center gap-1 lg:flex">
          <NavItems items={links} />
        </nav>

        {/* Desktop profile */}
        <div className="hidden items-center gap-2 lg:flex">
          <div className="relative">
            <button
              className="inline-flex items-center gap-2 rounded-xl border border-white/20 bg-white/10 px-3 py-2 text-sm font-medium text-white transition hover:bg-white/20"
              onClick={() => setProfileOpen((p) => !p)}
            >
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-white/20">
                <FiUser size={12} />
              </span>
              <span className="max-w-[160px] truncate">{user?.full_name || user?.email || "Account"}</span>
              <FiChevronDown
                size={14}
                className={`transition-transform ${profileOpen ? "rotate-180" : ""}`}
              />
            </button>

            <AnimatePresence>
              {profileOpen ? (
                <motion.div
                  initial={{ opacity: 0, y: -6, scale: 0.97 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -6, scale: 0.97 }}
                  transition={{ duration: 0.15 }}
                  className="absolute right-0 mt-2 w-52 rounded-xl border border-slate-200 bg-white p-2 shadow-card-hover"
                >
                  <div className="px-3 py-2">
                    <p className="text-xs font-semibold text-slate-900 truncate">{user?.email}</p>
                    <span className="app-badge-navy mt-1">Role: {user?.role || "user"}</span>
                  </div>
                  <div className="my-1 border-t border-slate-100" />
                  <button
                    className="inline-flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm font-medium text-red-600 transition hover:bg-red-50"
                    onClick={handleLogout}
                  >
                    <FiLogOut size={14} /> Sign out
                  </button>
                </motion.div>
              ) : null}
            </AnimatePresence>
          </div>
        </div>

        {/* Mobile toggle */}
        <button
          className="inline-flex items-center justify-center rounded-xl border border-white/20 bg-white/10 p-2 text-white lg:hidden"
          onClick={() => setMobileOpen((p) => !p)}
          aria-label="Toggle navigation menu"
        >
          {mobileOpen ? <FiX size={18} /> : <FiMenu size={18} />}
        </button>
      </div>

      {/* Mobile nav */}
      <AnimatePresence>
        {mobileOpen ? (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden border-t border-white/10 bg-navy-900 lg:hidden"
          >
            <div className="mx-auto max-w-7xl px-4 py-3 sm:px-6">
              <div className="flex flex-col gap-1">
                <NavItems items={links} onNavigate={() => setMobileOpen(false)} />
              </div>
              <div className="mt-3 border-t border-white/10 pt-3">
                <p className="mb-2 text-sm text-white/70">{user?.full_name || user?.email}</p>
                <button
                  className="inline-flex items-center gap-2 rounded-xl border border-white/20 bg-white/10 px-4 py-2 text-sm font-medium text-white"
                  onClick={handleLogout}
                >
                  <FiLogOut size={14} /> Sign out
                </button>
              </div>
            </div>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </header>
  );
}

export default Navbar;
