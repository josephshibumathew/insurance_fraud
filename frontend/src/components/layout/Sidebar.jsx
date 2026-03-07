import React, { useMemo, useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import {
  FiBarChart2,
  FiChevronLeft,
  FiChevronRight,
  FiClipboard,
  FiCpu,
  FiFileText,
  FiList,
  FiPlusSquare,
  FiUsers,
} from "react-icons/fi";

import { useAuth } from "../../contexts/AuthContext";

function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const location = useLocation();
  const { hasPermission, hasRole } = useAuth();

  const menuItems = useMemo(() => {
    if (hasRole("admin")) {
      return [
        { to: "/admin/dashboard", label: "Dashboard",  icon: FiBarChart2 },
        { to: "/admin/claims",    label: "All Claims",  icon: FiClipboard },
        { to: "/admin/reports",   label: "All Reports", icon: FiFileText },
        { to: "/admin/surveyors", label: "Surveyors",   icon: FiUsers },
        { to: "/admin/logs",      label: "Logs",        icon: FiList },
        { to: "/admin/ml-models", label: "ML Models",   icon: FiCpu },
      ];
    }
    return [
      { to: "/dashboard",  label: "Dashboard", icon: FiBarChart2 },
      { to: "/claims",     label: "Claims",    icon: FiClipboard, visible: hasPermission("claims", "read") },
      { to: "/claims/new", label: "New Claim", icon: FiPlusSquare, visible: hasPermission("claims", "create") },
      { to: "/reports",   label: "Reports",   icon: FiFileText,  visible: hasPermission("reports", "read") },
    ].filter((item) => item.visible !== false);
  }, [hasPermission, hasRole]);

  return (
    <aside className="hidden px-3 pb-4 pt-3 lg:block">
      <div
        className={`flex h-full flex-col rounded-2xl border border-slate-200/70 bg-white shadow-card transition-all duration-200 ${
          collapsed ? "w-[3.75rem]" : "w-60"
        }`}
      >
        {/* Header row */}
        <div
          className={`flex items-center border-b border-slate-100 py-3 ${
            collapsed ? "justify-center px-2" : "justify-between px-3"
          }`}
        >
          {!collapsed ? (
            <span className="text-[11px] font-semibold uppercase tracking-widest text-slate-400">
              Navigation
            </span>
          ) : null}
          <button
            className="rounded-lg border border-slate-200 bg-white p-1.5 text-slate-500 transition hover:border-navy-300 hover:bg-navy-50 hover:text-navy-700"
            onClick={() => setCollapsed((prev) => !prev)}
            aria-label="Toggle sidebar"
          >
            {collapsed ? <FiChevronRight size={13} /> : <FiChevronLeft size={13} />}
          </button>
        </div>

        {/* Nav items */}
        <nav className="flex flex-1 flex-col gap-0.5 overflow-y-auto p-2" aria-label="Sidebar navigation">
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isClaimsRoot = item.to === "/claims";
            const isClaimsActive =
              location.pathname === "/claims" || location.pathname.startsWith("/claims/");
            const isNewClaimPath = location.pathname === "/claims/new";
            const forceClaimsInactive = isClaimsRoot && isNewClaimPath;

            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/claims/new"}
                className={({ isActive }) => {
                  const active =
                    forceClaimsInactive
                      ? false
                      : isActive || (isClaimsRoot && isClaimsActive);
                  return [
                    "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all",
                    active
                      ? "bg-navy-900 text-white shadow-sm"
                      : "text-slate-600 hover:bg-navy-50/70 hover:text-navy-900",
                  ].join(" ");
                }}
                title={collapsed ? item.label : undefined}
              >
                <Icon size={16} className="shrink-0" />
                {!collapsed ? <span>{item.label}</span> : null}
              </NavLink>
            );
          })}
        </nav>
      </div>
    </aside>
  );
}

export default Sidebar;
