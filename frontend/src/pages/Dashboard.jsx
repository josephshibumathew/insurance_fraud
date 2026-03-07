import React, { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { FiAlertTriangle, FiCheckCircle, FiClipboard, FiTrendingUp } from "react-icons/fi";

import { dashboardApi } from "../services/api";
import { useAuth } from "../contexts/AuthContext";
import LoadingSpinner from "../components/common/LoadingSpinner";
import ErrorAlert from "../components/common/ErrorAlert";
import { formatDate, getFraudScoreLabel } from "../utils/formatters";

const cardMotion = {
  initial: { opacity: 0, y: 10 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.2 },
};

function Dashboard() {
  const [sortDir, setSortDir] = useState("desc");
  const { user } = useAuth();
  const userScope = user?.id || "anonymous";

  const statsQuery = useQuery({ queryKey: ["dashboard", userScope, "stats"], queryFn: async () => (await dashboardApi.stats()).data, enabled: Boolean(user?.id) });
  const trendsQuery = useQuery({ queryKey: ["dashboard", userScope, "trends"], queryFn: async () => (await dashboardApi.trends()).data, enabled: Boolean(user?.id) });
  const highRiskQuery = useQuery({ queryKey: ["dashboard", userScope, "high-risk"], queryFn: async () => (await dashboardApi.highRisk()).data, enabled: Boolean(user?.id) });
  const recentQuery = useQuery({ queryKey: ["dashboard", userScope, "recent-activity"], queryFn: async () => (await dashboardApi.recentActivity()).data, enabled: Boolean(user?.id) });

  const highRiskClaims = useMemo(() => {
    const rows = [...(highRiskQuery.data || [])];
    rows.sort((a, b) => (sortDir === "asc" ? (a.fraud_score || 0) - (b.fraud_score || 0) : (b.fraud_score || 0) - (a.fraud_score || 0)));
    return rows;
  }, [highRiskQuery.data, sortDir]);

  const loading = statsQuery.isLoading || trendsQuery.isLoading || highRiskQuery.isLoading || recentQuery.isLoading;
  const error = statsQuery.error || trendsQuery.error || highRiskQuery.error || recentQuery.error;

  if (loading) return <LoadingSpinner text="Loading dashboard..." />;

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="page-title">Dashboard Overview</h1>
        <div className="flex gap-2">
          <Link className="app-button" to="/claims/new">+ New Claim</Link>
          <Link className="app-button-secondary" to="/claims">Open Claims</Link>
        </div>
      </div>

      {error ? <ErrorAlert message={error.message || "Failed to load dashboard"} /> : null}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <motion.div {...cardMotion} className="app-card border-l-4 border-l-navy-900">
          <div className="mb-3 inline-flex rounded-xl bg-navy-900/10 p-2.5 text-navy-700"><FiClipboard size={18} /></div>
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Total Claims</p>
          <p className="mt-1 text-3xl font-bold tracking-tight text-slate-900">{statsQuery.data?.total_claims ?? 0}</p>
        </motion.div>
        <motion.div {...cardMotion} className="app-card border-l-4 border-l-red-500">
          <div className="mb-3 inline-flex rounded-xl bg-red-100 p-2.5 text-red-600"><FiTrendingUp size={18} /></div>
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Fraud Rate</p>
          <p className="mt-1 text-3xl font-bold tracking-tight text-slate-900">{((statsQuery.data?.fraud_rate || 0) * 100).toFixed(1)}%</p>
        </motion.div>
        <motion.div {...cardMotion} className="app-card border-l-4 border-l-amber-500">
          <div className="mb-3 inline-flex rounded-xl bg-amber-100 p-2.5 text-amber-600"><FiAlertTriangle size={18} /></div>
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Pending Reviews</p>
          <p className="mt-1 text-3xl font-bold tracking-tight text-slate-900">{statsQuery.data?.high_risk_count ?? 0}</p>
        </motion.div>
        <motion.div {...cardMotion} className="app-card border-l-4 border-l-emerald-500">
          <div className="mb-3 inline-flex rounded-xl bg-emerald-100 p-2.5 text-emerald-600"><FiCheckCircle size={18} /></div>
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Reviewed Claims</p>
          <p className="mt-1 text-3xl font-bold tracking-tight text-slate-900">{(statsQuery.data?.total_claims || 0) - (statsQuery.data?.high_risk_count || 0)}</p>
        </motion.div>
      </div>

      <div className="grid gap-3 lg:grid-cols-3">
        <motion.div {...cardMotion} className="app-card lg:col-span-2">
          <h2 className="mb-3 text-lg font-semibold text-slate-900">Fraud Trends</h2>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={trendsQuery.data?.trends || []}>
              <XAxis dataKey="date" tickFormatter={(value) => formatDate(value)} />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Line type="monotone" dataKey="fraud_count" stroke="#D64045" strokeWidth={2} name="Fraud Cases" dot={false} />
              <Line type="monotone" dataKey="total_claims" stroke="#222831" strokeWidth={2} name="Total Claims" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </motion.div>

        <motion.div {...cardMotion} className="app-card">
          <h2 className="mb-3 text-lg font-semibold text-slate-900">Recent Activity</h2>
          <div className="space-y-2">
            {(recentQuery.data?.items || []).slice(0, 6).map((activity, index) => (
              <motion.div
                key={`${activity.claim_id}-${activity.timestamp}`}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.04 }}
                className="rounded-xl border border-slate-200 bg-slate-50 p-2 text-sm"
              >
                <div className="font-medium text-slate-700">Claim #{activity.claim_id} · {activity.status}</div>
                <div className="text-xs text-slate-500">{formatDate(activity.timestamp)}</div>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>

        <motion.div {...cardMotion} className="app-card">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-lg font-semibold text-slate-900">High-Risk Claims</h2>
            <button className="app-button-secondary text-xs" onClick={() => setSortDir((prev) => (prev === "asc" ? "desc" : "asc"))}>
              Sort {sortDir === "asc" ? "↑" : "↓"}
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead>
                <tr className="border-b border-navy-900/10 bg-navy-900 text-white">
                  <th className="px-3 py-3 font-semibold">ID</th>
                  <th className="px-3 py-3 font-semibold">Policy</th>
                  <th className="px-3 py-3 font-semibold">Fraud Score</th>
                  <th className="px-3 py-3 font-semibold">Risk</th>
                  <th className="px-3 py-3 font-semibold">Status</th>
                </tr>
              </thead>
              <tbody>
                {highRiskClaims.map((claim, idx) => (
                  <tr key={claim.id} className={`border-b border-slate-100 last:border-none hover:bg-navy-50/50 ${idx % 2 === 1 ? "bg-slate-50/50" : ""}`}>
                    <td className="px-3 py-2.5 text-slate-700">{claim.id}</td>
                    <td className="px-3 py-2.5 font-medium text-slate-800">{claim.policy_number}</td>
                    <td className="px-3 py-2.5">
                      <span className={`app-badge ${
                        (claim.fraud_score || 0) >= 0.7 ? "app-badge-red" :
                        (claim.fraud_score || 0) >= 0.35 ? "app-badge-amber" : "app-badge-green"
                      }`}>
                        {(claim.fraud_score || 0).toFixed(3)}
                      </span>
                    </td>
                    <td className="px-3 py-2.5 text-slate-700">{getFraudScoreLabel(claim.fraud_score || 0)}</td>
                    <td className="px-3 py-2.5 text-slate-700">{claim.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </motion.div>
    </section>
  );
}

export default Dashboard;
