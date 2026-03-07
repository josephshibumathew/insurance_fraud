import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";

import { adminApi, reportApi } from "../services/api";
import LoadingSpinner from "../components/common/LoadingSpinner";
import ErrorAlert from "../components/common/ErrorAlert";
import Pagination from "../components/common/Pagination";
import { formatDate } from "../utils/formatters";

function AdminReports() {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  const reportsQuery = useQuery({
    queryKey: ["admin", "reports", page, pageSize],
    queryFn: async () => (await adminApi.reports({ page, page_size: pageSize })).data,
  });

  const downloadReport = async (reportId) => {
    const response = await reportApi.get(reportId);
    const url = URL.createObjectURL(new Blob([response.data], { type: "application/pdf" }));
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `report_${reportId}.pdf`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  if (reportsQuery.isLoading) return <LoadingSpinner text="Loading reports..." />;

  return (
    <section className="space-y-3">
      <h1 className="page-title">All Reports</h1>
      {reportsQuery.error ? <ErrorAlert message={reportsQuery.error.message || "Failed to load reports"} /> : null}

      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="app-card overflow-hidden p-0">
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead>
              <tr className="bg-navy-900 text-white">
                <th className="px-3 py-2">ID</th>
                <th className="px-3 py-2">Claim ID</th>
                <th className="px-3 py-2">Generated</th>
                <th className="px-3 py-2">Action</th>
              </tr>
            </thead>
            <tbody>
              {(reportsQuery.data?.items || []).map((report) => (
                <tr key={report.id} className="border-b border-slate-100 last:border-none">
                  <td className="px-3 py-2">{report.id}</td>
                  <td className="px-3 py-2">{report.claim_id}</td>
                  <td className="px-3 py-2">{formatDate(report.created_at)}</td>
                  <td className="px-3 py-2">
                    <button className="app-button-secondary" onClick={() => downloadReport(report.id)}>
                      Download PDF
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="p-4">
          <Pagination
            page={page}
            pageSize={pageSize}
            total={reportsQuery.data?.total || 0}
            onPageChange={setPage}
            onPageSizeChange={(nextPageSize) => {
              setPageSize(nextPageSize);
              setPage(1);
            }}
          />
        </div>
      </motion.div>
    </section>
  );
}

export default AdminReports;
