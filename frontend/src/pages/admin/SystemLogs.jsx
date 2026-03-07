import React, { useEffect, useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";

import LoadingSpinner from "../../components/common/LoadingSpinner";
import ErrorAlert from "../../components/common/ErrorAlert";
import useSystemLogs from "../../hooks/useSystemLogs";

const LEVEL_CLASS = {
  INFO: "text-emerald-300",
  WARNING: "text-amber-300",
  ERROR: "text-red-300",
  DEBUG: "text-slate-300",
  CRITICAL: "text-fuchsia-300",
};

function SystemLogs() {
  const [lines, setLines] = useState(200);
  const containerRef = useRef(null);
  const { entries, surveyors, mlModels, environment, isLoading, isError, error } = useSystemLogs(lines);

  useEffect(() => {
    if (!containerRef.current) return;
    containerRef.current.scrollTop = containerRef.current.scrollHeight;
  }, [entries.length]);

  const modelSummary = useMemo(() => {
    if (!mlModels) return [];
    return [
      {
        label: "Ensemble",
        value: mlModels?.ensemble_model?.name || "-",
        path: mlModels?.ensemble_model?.path || "-",
      },
      {
        label: "YOLO",
        value: mlModels?.yolo_model?.name || "-",
        path: mlModels?.yolo_model?.path || "-",
      },
      {
        label: "Preprocessor",
        value: mlModels?.preprocessor?.status || "-",
        path: mlModels?.preprocessor?.path || "-",
      },
    ];
  }, [mlModels]);

  if (isLoading) {
    return <LoadingSpinner text="Loading system logs..." />;
  }

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold text-slate-900">System Logs</h1>
        <div className="flex items-center gap-2">
          <span className="text-sm text-slate-600">Lines</span>
          <select className="app-input w-40" value={lines} onChange={(event) => setLines(Number(event.target.value))}>
            <option value={100}>Last 100</option>
            <option value={200}>Last 200</option>
            <option value={500}>Last 500</option>
            <option value={1000}>Last 1000</option>
          </select>
        </div>
      </div>

      {isError ? <ErrorAlert message={error?.message || "Failed to load system logs"} /> : null}

      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="app-card">
        <div className="mb-3 flex flex-wrap items-center gap-4 text-sm text-slate-600">
          <span>Environment: <strong className="text-slate-900">{environment}</strong></span>
          <span>Surveyors: <strong className="text-slate-900">{surveyors.length}</strong></span>
          <span>Polling: <strong className="text-slate-900">Every 3s</strong></span>
        </div>

        <div ref={containerRef} className="h-[30rem] overflow-auto rounded-xl border border-slate-700 bg-slate-950 p-3 font-mono text-xs">
          {entries.length === 0 ? (
            <div className="text-slate-400">No logs available.</div>
          ) : (
            entries.map((entry, index) => (
              <div key={`${entry.id}-${index}`} className="mb-1 break-words text-slate-100">
                <span className="mr-2 text-slate-400">{entry.timestamp || "-"}</span>
                <span className={`mr-2 font-semibold ${LEVEL_CLASS[entry.level] || LEVEL_CLASS.INFO}`}>[{entry.level}]</span>
                <span className="mr-2 text-cyan-300">[{entry.source}]</span>
                <span>{entry.message}</span>
              </div>
            ))
          )}
        </div>
      </motion.div>

      <div className="grid gap-3 lg:grid-cols-2">
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="app-card">
          <h2 className="mb-3 text-lg font-semibold text-slate-900">Surveyors</h2>
          <div className="max-h-64 overflow-auto rounded-lg border border-slate-200">
            <table className="min-w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-slate-600">
                  <th className="px-2 py-2">ID</th>
                  <th className="px-2 py-2">Email</th>
                  <th className="px-2 py-2">Claims</th>
                </tr>
              </thead>
              <tbody>
                {surveyors.map((surveyor) => (
                  <tr key={surveyor.id} className="border-b border-slate-100 last:border-none">
                    <td className="px-2 py-2">{surveyor.id}</td>
                    <td className="px-2 py-2">{surveyor.email}</td>
                    <td className="px-2 py-2">{surveyor.total_claims}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="app-card">
          <h2 className="mb-3 text-lg font-semibold text-slate-900">Current ML Models</h2>
          <div className="space-y-3 text-sm">
            {modelSummary.map((model) => (
              <div key={model.label} className="rounded-lg border border-slate-200 p-3">
                <div className="font-semibold text-slate-800">{model.label}: {model.value}</div>
                <div className="text-slate-500">{model.path}</div>
              </div>
            ))}
          </div>
        </motion.div>
      </div>
    </section>
  );
}

export default SystemLogs;
