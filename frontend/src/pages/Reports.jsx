import React, { useMemo, useState } from "react";
import { useMutation, useQueries, useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { toast } from "react-toastify";
import { FiDownload, FiEye, FiRefreshCcw, FiSearch } from "react-icons/fi";

import ErrorAlert from "../components/common/ErrorAlert";
import LoadingSpinner from "../components/common/LoadingSpinner";
import ReportPreview from "../components/reports/ReportPreview";
import { claimsApi, fraudApi, reportApi } from "../services/api";
import { getClaimExtendedFields } from "../utils/claimFieldStore";
import { formatDate } from "../utils/formatters";

function Reports() {
  const [error, setError] = useState("");
  const [previewContext, setPreviewContext] = useState(null);
  const [search, setSearch] = useState("");

  const claimsQuery = useQuery({
    queryKey: ["claims", "reports-page"],
    queryFn: async () => (await claimsApi.list({ page: 1, page_size: 100 })).data,
  });

  const reportQueries = useQueries({
    queries: (claimsQuery.data?.items || []).map((claim) => ({
      queryKey: ["report", "latest", claim.id],
      queryFn: async () => {
        try {
          const response = await reportApi.latestForClaim(claim.id);
          return { claim, report: response.data };
        } catch (_error) {
          return null;
        }
      },
      enabled: Boolean(claimsQuery.data?.items),
    })),
  });

  const reports = useMemo(() => {
    const result = reportQueries.map((query) => query.data).filter(Boolean);
    if (!search.trim()) return result;

    const needle = search.trim().toLowerCase();
    return result.filter((entry) => String(entry.claim.id).includes(needle) || String(entry.report.id).includes(needle));
  }, [reportQueries, search]);

  const regenerateMutation = useMutation({
    mutationFn: (claimId) => reportApi.generate(claimId),
    onSuccess: () => {
      toast.success("Report generated");
      claimsQuery.refetch();
    },
    onError: (mutationError) => {
      const message = mutationError.response?.data?.detail || "Failed to regenerate report";
      setError(message);
      toast.error(message);
    },
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

  const openPreview = async (entry) => {
    try {
      const [fraudResponse, imageResponse] = await Promise.all([
        fraudApi.results(entry.claim.id).catch(() => ({ data: null })),
        claimsApi.listImages(entry.claim.id).catch(() => ({ data: [] })),
      ]);

      setPreviewContext({
        claim: entry.claim,
        reportId: entry.report.id,
        fraud: fraudResponse.data,
        images: imageResponse.data || [],
        extendedFields: getClaimExtendedFields(entry.claim.id),
      });
    } catch (_previewError) {
      toast.error("Unable to load preview details");
    }
  };

  if (claimsQuery.isLoading) return <LoadingSpinner text="Loading reports..." />;

  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="page-title">Generated Reports</h1>
      </div>

      {error ? <ErrorAlert message={error} onClose={() => setError("")} /> : null}

      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="app-card">
        <div className="relative max-w-sm">
          <FiSearch className="pointer-events-none absolute left-3 top-2.5 text-slate-400" />
          <input className="app-input pl-9" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search by claim or report ID" />
        </div>
      </motion.div>

      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="app-card overflow-hidden p-0">
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead>
              <tr className="bg-navy-900 text-white">
                <th className="px-3 py-2">Report ID</th>
                <th className="px-3 py-2">Claim ID</th>
                <th className="px-3 py-2">Generated</th>
                <th className="px-3 py-2">Fraud Score</th>
                <th className="px-3 py-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {reports.map((entry) => (
                <tr key={entry.report.id} className="border-b border-slate-100 last:border-none">
                  <td className="px-3 py-2">{entry.report.id}</td>
                  <td className="px-3 py-2">{entry.claim.id}</td>
                  <td className="px-3 py-2">{formatDate(entry.report.created_at)}</td>
                  <td className="px-3 py-2">{entry.claim.fraud_score != null ? Number(entry.claim.fraud_score).toFixed(3) : "-"}</td>
                  <td className="px-3 py-2">
                    <div className="flex flex-wrap gap-2">
                      <button className="app-button-secondary" onClick={() => openPreview(entry)}>
                        <FiEye className="mr-1" /> Preview
                      </button>
                      <button className="app-button" onClick={() => downloadReport(entry.report.id)}>
                        <FiDownload className="mr-1" /> Download
                      </button>
                      <button
                        className="app-button-secondary"
                        onClick={() => regenerateMutation.mutate(entry.claim.id)}
                        disabled={regenerateMutation.isPending}
                      >
                        <FiRefreshCcw className="mr-1" /> Regenerate
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {reports.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-3 py-6 text-center text-slate-500">No generated reports found yet.</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </motion.div>

      {previewContext ? (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
          <ReportPreview
            claim={previewContext.claim}
            extendedFields={previewContext.extendedFields}
            fraud={previewContext.fraud}
            images={previewContext.images}
            reportId={previewContext.reportId}
            onDownload={() => downloadReport(previewContext.reportId)}
          />
        </motion.div>
      ) : null}
    </section>
  );
}

export default Reports;
