import React from "react";
import { Outlet } from "react-router-dom";
import { motion } from "framer-motion";

import Footer from "./Footer";
import Navbar from "./Navbar";
import Sidebar from "./Sidebar";

function Layout() {
  return (
    <div className="flex min-h-screen flex-col" style={{ backgroundColor: "var(--bg)" }}>
      <Navbar />
      <div className="mx-auto flex w-full max-w-7xl flex-1" style={{ minHeight: 0 }}>
        <Sidebar />
        <main className="w-full overflow-auto px-3 pb-8 pt-4 sm:px-5 lg:px-6" aria-live="polite">
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.22, ease: "easeOut" }}
          >
            <Outlet />
          </motion.div>
        </main>
      </div>
      <Footer />
    </div>
  );
}

export default Layout;
