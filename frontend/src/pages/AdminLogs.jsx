import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";

import { adminApi } from "../services/api";
import LoadingSpinner from "../components/common/LoadingSpinner";
import ErrorAlert from "../components/common/ErrorAlert";

function AdminLogs() {
  const [lines, setLines] = useState(200);

  const logsQuery = useQuery({
    queryKey: ["admin", "logs", lines],
    queryFn: async () => (await adminApi.logs({ lines })).data,
  });

  if (logsQuery.isLoading) return <LoadingSpinner text="Loading logs..." />;

  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-2xl font-bold text-slate-900">System Logs</h1>
        <select className="app-input w-40" value={lines} onChange={(event) => setLines(Number(event.target.value))}>
          <option value={100}>Last 100 lines</option>
          <option value={200}>Last 200 lines</option>
          <option value={500}>Last 500 lines</option>
          <option value={1000}>Last 1000 lines</option>
        </select>
      </div>

      {logsQuery.error ? <ErrorAlert message={logsQuery.error.message || "Failed to load logs"} /> : null}

      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="app-card">
        <div className="mb-3 grid gap-2 text-sm text-slate-600 sm:grid-cols-3">
          <p>Environment: <span className="font-semibold text-slate-900">{logsQuery.data?.environment || "unknown"}</span></p>
          <p>Surveyors: <span className="font-semibold text-slate-900">{logsQuery.data?.surveyor_count ?? 0}</span></p>
          <p>Lines requested: <span className="font-semibold text-slate-900">{logsQuery.data?.requested_lines ?? lines}</span></p>
        </div>

        <div className="grid gap-3 lg:grid-cols-3">
          {Object.entries(logsQuery.data?.logs || {}).map(([name, logData]) => (
            <div key={name} className="space-y-2">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">{name} logs</h2>
              <p className="truncate text-xs text-slate-500">{logData.file}</p>
              <div className="max-h-[420px] overflow-auto rounded-xl border border-slate-200 bg-slate-900 p-3 font-mono text-xs text-slate-100">
                {(logData.lines || []).length === 0 ? (
                  <div className="text-slate-400">No log lines available yet.</div>
                ) : (
                  (logData.lines || []).map((line, index) => <div key={`${name}-${index}-${line}`}>{line}</div>)
                )}
              </div>
            </div>
          ))}
        </div>
      </motion.div>

      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="app-card">
        <h2 className="mb-3 text-lg font-semibold text-slate-900">Registered Surveyors</h2>
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500">
                <th className="px-2 py-2">ID</th>
                <th className="px-2 py-2">Name</th>
                <th className="px-2 py-2">Email</th>
                <th className="px-2 py-2">Active</th>
                <th className="px-2 py-2">Claims</th>
              </tr>
            </thead>
            <tbody>
              {(logsQuery.data?.surveyors || []).map((surveyor) => (
                <tr key={surveyor.id} className="border-b border-slate-100 last:border-none">
                  <td className="px-2 py-2">{surveyor.id}</td>
                  <td className="px-2 py-2">{surveyor.full_name || "-"}</td>
                  <td className="px-2 py-2">{surveyor.email}</td>
                  <td className="px-2 py-2">{surveyor.is_active ? "Yes" : "No"}</td>
                  <td className="px-2 py-2">{surveyor.total_claims}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </motion.div>

      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="app-card">
        <h2 className="mb-3 text-lg font-semibold text-slate-900">Current ML Models</h2>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 text-sm">
          <div>
            <p className="font-semibold text-slate-800">Ensemble</p>
            <p className="text-slate-600">{logsQuery.data?.ml_models?.ensemble_model?.name || "-"}</p>
            <p className="text-slate-500">{logsQuery.data?.ml_models?.ensemble_model?.path || "-"}</p>
          </div>
          <div>
            <p className="font-semibold text-slate-800">YOLO</p>
            <p className="text-slate-600">{logsQuery.data?.ml_models?.yolo_model?.name || "-"}</p>
            <p className="text-slate-500">{logsQuery.data?.ml_models?.yolo_model?.path || "-"}</p>
          </div>
          <div>
            <p className="font-semibold text-slate-800">Preprocessor</p>
            <p className="text-slate-600">{logsQuery.data?.ml_models?.preprocessor?.status || "-"}</p>
            <p className="text-slate-500">{logsQuery.data?.ml_models?.preprocessor?.path || "-"}</p>
          </div>
        </div>
      </motion.div>
    </section>
  );
}

export default AdminLogs;
