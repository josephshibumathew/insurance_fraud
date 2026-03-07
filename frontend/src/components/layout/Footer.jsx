import React from "react";
import { FiShield } from "react-icons/fi";

function Footer() {
  return (
    <footer className="border-t border-navy-900/10 bg-white/60 px-4 py-3">
      <div className="mx-auto flex w-full max-w-7xl flex-wrap items-center justify-between gap-2">
        <span className="flex items-center gap-2 text-xs text-slate-500">
          <FiShield size={12} className="text-navy-500" />
          &copy; {new Date().getFullYear()}{" "}
          <span className="font-medium text-slate-700">AutoFraud Intelligence</span>
        </span>
        <span className="text-xs text-slate-400">Fraud Detection Platform v1.0</span>
      </div>
    </footer>
  );
}

export default Footer;
