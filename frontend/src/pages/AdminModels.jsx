import React from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";

import { adminApi } from "../services/api";
import LoadingSpinner from "../components/common/LoadingSpinner";
import ErrorAlert from "../components/common/ErrorAlert";

function AdminModels() {
  const modelsQuery = useQuery({
    queryKey: ["admin", "models"],
    queryFn: async () => (await adminApi.models()).data,
  });

  if (modelsQuery.isLoading) return <LoadingSpinner text="Loading ML model details..." />;

  return (
    <section className="space-y-3">
      <h1 className="page-title">ML Model Info</h1>
      {modelsQuery.error ? <ErrorAlert message={modelsQuery.error.message || "Failed to load model info"} /> : null}

      <div className="grid gap-3 lg:grid-cols-3">
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="app-card">
          <h2 className="mb-2 text-lg font-semibold text-slate-900">Ensemble</h2>
          <p className="text-sm text-slate-600">Name: {modelsQuery.data?.ensemble_model?.name || "-"}</p>
          <p className="text-sm text-slate-600">Version: {modelsQuery.data?.ensemble_model?.version || "-"}</p>
          <p className="text-sm text-slate-600">Path: {modelsQuery.data?.ensemble_model?.path || "-"}</p>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="app-card">
          <h2 className="mb-2 text-lg font-semibold text-slate-900">YOLO</h2>
          <p className="text-sm text-slate-600">Name: {modelsQuery.data?.yolo_model?.name || "-"}</p>
          <p className="text-sm text-slate-600">Version: {modelsQuery.data?.yolo_model?.version || "-"}</p>
          <p className="text-sm text-slate-600">Path: {modelsQuery.data?.yolo_model?.path || "-"}</p>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="app-card">
          <h2 className="mb-2 text-lg font-semibold text-slate-900">Configuration</h2>
          <p className="text-sm text-slate-600">Preprocessor: {modelsQuery.data?.preprocessor?.status || "-"}</p>
          <p className="text-sm text-slate-600">Config File: {modelsQuery.data?.config_file || "-"}</p>
          <p className="text-sm text-slate-600">Config Exists: {modelsQuery.data?.config_file_exists ? "Yes" : "No"}</p>
        </motion.div>
      </div>
    </section>
  );
}

export default AdminModels;
