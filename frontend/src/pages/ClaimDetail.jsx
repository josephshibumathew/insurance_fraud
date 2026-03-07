import React, { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { toast } from "react-toastify";

import ErrorAlert from "../components/common/ErrorAlert";
import LoadingSpinner from "../components/common/LoadingSpinner";
import ReportPreview from "../components/reports/ReportPreview";
import { claimsApi, fraudApi, imageApi, reportApi } from "../services/api";
import { getClaimExtendedFields } from "../utils/claimFieldStore";
import { formatCurrency, formatDate, getFraudScoreLabel, getFraudScoreVariant } from "../utils/formatters";
import { normalizeShapValues, summarizeShapFactors } from "../utils/shap";

function ClaimDetail() {
  const { claimId } = useParams();
  const [showReportPreview, setShowReportPreview] = useState(false);

  const claimQuery = useQuery({ queryKey: ["claim", claimId], queryFn: async () => (await claimsApi.get(claimId)).data });
  const fraudStatusQuery = useQuery({ queryKey: ["fraud-status", claimId], queryFn: async () => (await fraudApi.status(claimId)).data, retry: 0 });
  const fraudQuery = useQuery({
    queryKey: ["fraud", claimId],
    queryFn: async () => (await fraudApi.results(claimId)).data,
    enabled: fraudStatusQuery.data?.status === "completed",
    retry: 0,
  });
  const predictMutation = useMutation({
    mutationFn: () => fraudApi.predict(claimId),
    onSuccess: () => {
      toast.success("Fraud prediction completed");
      fraudQuery.refetch();
      fraudStatusQuery.refetch();
    },
    onError: () => toast.error("Failed to run fraud prediction"),
  });

  const imagesQuery = useQuery({ queryKey: ["claim-images", claimId], queryFn: async () => (await claimsApi.listImages(claimId)).data, retry: 0 });
  const reportQuery = useQuery({ queryKey: ["latest-report", claimId], queryFn: async () => (await reportApi.latestForClaim(claimId)).data, retry: 0 });

  const generateReportMutation = useMutation({
    mutationFn: () => reportApi.generate(claimId),
    onSuccess: () => {
      toast.success("Report generated");
      setShowReportPreview(true);
      reportQuery.refetch();
    },
    onError: () => toast.error("Report generation failed"),
  });

  const claim = claimQuery.data;
  const extendedFields = useMemo(() => getClaimExtendedFields(claimId), [claimId]);

  const normalizedShap = useMemo(() => normalizeShapValues(fraudQuery.data?.shap_values || {}), [fraudQuery.data]);
  const shapSummary = useMemo(() => summarizeShapFactors(normalizedShap), [normalizedShap]);

  useEffect(() => {
    if (fraudStatusQuery.data?.status === "pending" && !predictMutation.isPending && !predictMutation.isSuccess) {
      predictMutation.mutate();
    }
  }, [fraudStatusQuery.data?.status, predictMutation]);

  if (claimQuery.isLoading) return <LoadingSpinner text="Loading claim details..." />;
  if (claimQuery.error) return <ErrorAlert message="Unable to load claim details" />;

  const fraudScoreRaw = fraudQuery.data?.fusion_score ?? fraudQuery.data?.ensemble_score ?? claim.fraud_score;
  const fraudScore = Number.isFinite(Number(fraudScoreRaw)) ? Number(fraudScoreRaw) : 0;

  const downloadReport = async () => {
    if (!reportQuery.data?.id) return;
    const response = await reportApi.get(reportQuery.data.id);
    const blobUrl = window.URL.createObjectURL(new Blob([response.data], { type: "application/pdf" }));
    const link = document.createElement("a");
    link.href = blobUrl;
    link.download = `claim_${claimId}_report.pdf`;
    link.click();
    window.URL.revokeObjectURL(blobUrl);
  };

  return (
    <section className="space-y-4">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="page-title">Claim #{claim.id}</h1>
        <div className="flex flex-wrap gap-2">
          <button
            className="app-button"
            onClick={() => generateReportMutation.mutate()}
            disabled={generateReportMutation.isPending}
          >
            {generateReportMutation.isPending ? "Generating..." : "Generate Report"}
          </button>
          <button
            className="app-button-secondary"
            onClick={downloadReport}
            disabled={!reportQuery.data?.id}
          >
            Download PDF
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        {/* Claim information */}
        <motion.div whileHover={{ y: -2 }} className="app-card lg:col-span-5">
          <h2 className="mb-4 text-base font-semibold text-slate-900">Claim Information</h2>
          <dl className="space-y-2.5">
            {[
              ["Policy Number", claim.policy_number],
              ["Policy Type", extendedFields?.policy_type || "-"],
              ["Claim Amount", formatCurrency(claim.claim_amount)],
              ["Accident Date", formatDate(claim.accident_date)],
              ["Location", extendedFields?.accident_location || "-"],
              ["Status", claim.status],
            ].map(([label, value]) => (
              <div key={label} className="flex items-start justify-between gap-3">
                <dt className="w-2/5 shrink-0 text-sm text-slate-500">{label}</dt>
                <dd className="text-right text-sm font-medium text-slate-800">{value}</dd>
              </div>
            ))}
          </dl>
        </motion.div>

        {/* Fraud score */}
        <motion.div whileHover={{ y: -2 }} className="app-card lg:col-span-7">
          <h2 className="mb-4 text-base font-semibold text-slate-900">Fraud Score</h2>

          {/* Score bar */}
          <div className="relative h-3 w-full overflow-hidden rounded-full bg-slate-100">
            <div
              className={`h-full rounded-full transition-all ${
                fraudScore >= 0.7 ? "bg-red-500" :
                fraudScore >= 0.35 ? "bg-amber-500" : "bg-emerald-500"
              }`}
              style={{ width: `${Math.min(100, fraudScore * 100)}%` }}
              role="meter"
              aria-label="Fraud score indicator"
              aria-valuemin={0}
              aria-valuemax={1}
              aria-valuenow={fraudScore}
            />
          </div>
          <div className="mt-2 flex items-center justify-between">
            <span className="text-2xl font-bold tracking-tight text-slate-900">
              {(fraudScore * 100).toFixed(1)}%
            </span>
            <span className={`app-badge ${
              fraudScore >= 0.7 ? "app-badge-red" :
              fraudScore >= 0.35 ? "app-badge-amber" : "app-badge-green"
            }`}>
              {getFraudScoreLabel(fraudScore)} Risk
            </span>
          </div>

          <div className="mt-4 space-y-1.5">
            <p className="text-xs text-slate-500">
              <span className="font-medium text-red-600">Risk-up factors: </span>
              {shapSummary.increasing.join(", ") || "None"}
            </p>
            <p className="text-xs text-slate-500">
              <span className="font-medium text-emerald-600">Risk-down factors: </span>
              {shapSummary.decreasing.join(", ") || "None"}
            </p>
          </div>
        </motion.div>

        {/* SHAP chart */}
        <motion.div whileHover={{ y: -2 }} className="app-card lg:col-span-6">
          <h2 className="mb-3 text-base font-semibold text-slate-900">SHAP Feature Importance</h2>
          {normalizedShap.length === 0 ? (
            <p className="text-sm text-slate-500">SHAP values will appear after prediction is generated.</p>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={normalizedShap.slice(0, 10)} layout="vertical">
                <XAxis type="number" tick={{ fontSize: 11 }} />
                <YAxis type="category" dataKey="label" width={160} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="value">
                  {normalizedShap.slice(0, 10).map((entry) => (
                    <Cell key={entry.feature} fill={entry.value >= 0 ? "#D64045" : "#06A77D"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </motion.div>

        {/* Damage assessment */}
        <motion.div whileHover={{ y: -2 }} className="app-card lg:col-span-6">
          <h2 className="mb-3 text-base font-semibold text-slate-900">Damage Assessment</h2>
          {imagesQuery.isLoading ? <LoadingSpinner text="Loading images..." /> : null}
          {imagesQuery.error ? <ErrorAlert message="Unable to load claim images" /> : null}
          <div className="space-y-2">
            {(imagesQuery.data || []).map((image) => (
              <div key={image.id} className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                <p className="text-sm font-semibold text-slate-800">Image #{image.id}</p>
                <p className="text-xs text-slate-500">
                  Severity: {image.damage_results?.severity_score ?? "-"} &middot;{" "}
                  Parts: {(image.damage_results?.affected_parts || []).join(", ") || "-"}
                </p>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Damage images */}
        <motion.div whileHover={{ y: -2 }} className="app-card lg:col-span-12">
          <h2 className="mb-3 text-base font-semibold text-slate-900">Damage Images (with bounding boxes)</h2>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {(imagesQuery.data || []).map((image) => (
              <div key={image.id} className="relative overflow-hidden rounded-xl border border-slate-200">
                <img
                  src={imageApi.visualization(image.id)}
                  alt={`Damage visualization ${image.id}`}
                  className="w-full"
                  loading="lazy"
                />
                {(image.damage_results?.bounding_boxes || []).map((box, index) => (
                  <div
                    key={index}
                    className="absolute border-2 border-red-500"
                    style={{ left: box.x, top: box.y, width: box.w, height: box.h }}
                    aria-hidden="true"
                  />
                ))}
              </div>
            ))}
          </div>
        </motion.div>

        {(showReportPreview || reportQuery.data?.id) && (
          <div className="lg:col-span-12">
            <ReportPreview
              claim={claim}
              extendedFields={extendedFields}
              fraud={fraudQuery.data}
              images={imagesQuery.data || []}
              reportId={reportQuery.data?.id}
              onDownload={downloadReport}
            />
          </div>
        )}
      </div>
    </section>
  );
}

export default ClaimDetail;
