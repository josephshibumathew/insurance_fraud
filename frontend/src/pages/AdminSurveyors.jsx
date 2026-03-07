import React from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";

import { adminApi } from "../services/api";
import LoadingSpinner from "../components/common/LoadingSpinner";
import ErrorAlert from "../components/common/ErrorAlert";
import { formatDate } from "../utils/formatters";

function AdminSurveyors() {
  const surveyorsQuery = useQuery({
    queryKey: ["admin", "surveyors"],
    queryFn: async () => (await adminApi.surveyors()).data,
  });

  if (surveyorsQuery.isLoading) return <LoadingSpinner text="Loading surveyors..." />;

  return (
    <section className="space-y-3">
      <h1 className="page-title">Surveyors</h1>
      {surveyorsQuery.error ? <ErrorAlert message={surveyorsQuery.error.message || "Failed to load surveyors"} /> : null}

      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="app-card overflow-hidden p-0">
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead>
              <tr className="bg-navy-900 text-white">
                <th className="px-3 py-2">ID</th>
                <th className="px-3 py-2">Name</th>
                <th className="px-3 py-2">Email</th>
                <th className="px-3 py-2">Claims</th>
                <th className="px-3 py-2">Created</th>
              </tr>
            </thead>
            <tbody>
              {(surveyorsQuery.data || []).map((surveyor) => (
                <tr key={surveyor.id} className="border-b border-slate-100 last:border-none">
                  <td className="px-3 py-2">{surveyor.id}</td>
                  <td className="px-3 py-2">{surveyor.full_name || "-"}</td>
                  <td className="px-3 py-2">{surveyor.email}</td>
                  <td className="px-3 py-2">{surveyor.total_claims}</td>
                  <td className="px-3 py-2">{formatDate(surveyor.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </motion.div>
    </section>
  );
}

export default AdminSurveyors;
