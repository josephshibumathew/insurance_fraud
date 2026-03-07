import React from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";

import { adminApi } from "../services/api";
import LoadingSpinner from "../components/common/LoadingSpinner";
import ErrorAlert from "../components/common/ErrorAlert";
import { formatDate } from "../utils/formatters";

function AdminDashboard() {
  const statsQuery = useQuery({
    queryKey: ["admin", "dashboard", "stats"],
    queryFn: async () => (await adminApi.stats()).data,
  });

  if (statsQuery.isLoading) return <LoadingSpinner text="Loading admin dashboard..." />;

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="page-title">Admin Dashboard</h1>
      </div>

      {statsQuery.error ? <ErrorAlert message={statsQuery.error.message || "Failed to load admin stats"} /> : null}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {[
          { label: "Total Claims", value: statsQuery.data?.total_claims ?? 0, border: "border-l-navy-900" },
          { label: "Fraud Rate", value: `${((statsQuery.data?.fraud_rate || 0) * 100).toFixed(1)}%`, border: "border-l-red-500" },
          { label: "High-Risk Claims", value: statsQuery.data?.high_risk_count ?? 0, border: "border-l-amber-500" },
          { label: "Surveyors", value: statsQuery.data?.surveyor_count ?? 0, border: "border-l-teal-500" },
          { label: "Reports Generated", value: statsQuery.data?.reports_generated ?? 0, border: "border-l-slate-400" },
        ].map(({ label, value, border }) => (
          <motion.div key={label} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className={`app-card border-l-4 ${border}`}>
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
            <p className="mt-1 text-3xl font-bold tracking-tight text-slate-900">{value}</p>
          </motion.div>
        ))}
      </div>

      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="app-card">
        <h2 className="mb-3 text-lg font-semibold text-slate-900">Recent Claims Activity</h2>
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead>
              <tr className="bg-navy-900 text-white">
                <th className="px-2 py-2">Claim ID</th>
                <th className="px-2 py-2">User ID</th>
                <th className="px-2 py-2">Status</th>
                <th className="px-2 py-2">Fraud Score</th>
                <th className="px-2 py-2">Created</th>
              </tr>
            </thead>
            <tbody>
              {(statsQuery.data?.recent_activity || []).map((activity) => (
                <tr key={`${activity.claim_id}-${activity.created_at}`} className="border-b border-slate-100 last:border-none">
                  <td className="px-2 py-2">{activity.claim_id}</td>
                  <td className="px-2 py-2">{activity.user_id}</td>
                  <td className="px-2 py-2">{activity.status}</td>
                  <td className="px-2 py-2">{activity.fraud_score != null ? Number(activity.fraud_score).toFixed(3) : "-"}</td>
                  <td className="px-2 py-2">{formatDate(activity.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </motion.div>
    </section>
  );
}

export default AdminDashboard;
