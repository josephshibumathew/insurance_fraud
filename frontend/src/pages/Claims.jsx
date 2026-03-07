import React, { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { toast } from "react-toastify";

import useClaims from "../hooks/useClaims";
import { claimsApi, fraudApi } from "../services/api";
import ConfirmationModal from "../components/common/ConfirmationModal";
import ErrorAlert from "../components/common/ErrorAlert";
import LoadingSpinner from "../components/common/LoadingSpinner";
import Pagination from "../components/common/Pagination";
import { formatCurrency, formatDate, getFraudScoreVariant } from "../utils/formatters";

const FRAUD_BADGE_CLASS = {
  success: "bg-emerald-500",
  warning: "bg-amber-500",
  danger: "bg-red-500",
};

function Claims() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [selectedIds, setSelectedIds] = useState([]);
  const [error, setError] = useState("");

  const claims = useClaims(10);
  const items = useMemo(() => claims.data?.items || [], [claims.data]);

  const batchPredictMutation = useMutation({
    mutationFn: () => fraudApi.batch(selectedIds),
    onSuccess: () => {
      toast.success("Batch prediction completed");
      queryClient.invalidateQueries({ queryKey: ["claims"] });
    },
    onError: (err) => setError(err.response?.data?.detail || "Batch prediction failed"),
  });

  const exportSelected = () => {
    const selected = items.filter((item) => selectedIds.includes(item.id));
    const csv = ["id,policy_number,claim_amount,fraud_score,status", ...selected.map((row) => `${row.id},${row.policy_number},${row.claim_amount},${row.fraud_score ?? ""},${row.status}`)].join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "claims-export.csv";
    link.click();
    URL.revokeObjectURL(url);
  };

  const toggleSelect = (id) => {
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]));
  };

  if (claims.isLoading) return <LoadingSpinner text="Loading claims..." />;

  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="page-title">Claims</h1>
      </div>
      {error && <ErrorAlert message={error} onClose={() => setError("")} />}

      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="app-card">
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-7">
          <input className="app-input lg:col-span-2" placeholder="Search policy number" value={claims.search} onChange={(e) => claims.setSearch(e.target.value)} />
          <select className="app-input" value={claims.filters.status} onChange={(e) => claims.setFilters((prev) => ({ ...prev, status: e.target.value }))}>
            <option value="">All Statuses</option>
            <option value="submitted">Submitted</option>
            <option value="under_review">Under Review</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
          </select>
          <input className="app-input" type="date" value={claims.filters.fromDate} onChange={(e) => claims.setFilters((prev) => ({ ...prev, fromDate: e.target.value }))} />
          <input className="app-input" type="date" value={claims.filters.toDate} onChange={(e) => claims.setFilters((prev) => ({ ...prev, toDate: e.target.value }))} />
          <input className="app-input" placeholder="Min risk" type="number" min="0" max="1" step="0.01" value={claims.filters.minFraudScore} onChange={(e) => claims.setFilters((prev) => ({ ...prev, minFraudScore: e.target.value }))} />
          <input className="app-input" placeholder="Max risk" type="number" min="0" max="1" step="0.01" value={claims.filters.maxFraudScore} onChange={(e) => claims.setFilters((prev) => ({ ...prev, maxFraudScore: e.target.value }))} />
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          <button className="app-button-secondary" onClick={() => claims.refetch()}>Apply Filters</button>
          <button className="app-button-secondary" disabled={selectedIds.length === 0} onClick={exportSelected}>Export Selected</button>
          <button className="app-button" disabled={selectedIds.length === 0 || batchPredictMutation.isPending} onClick={() => batchPredictMutation.mutate()}>
            {batchPredictMutation.isPending ? "Predicting..." : "Batch Predict"}
          </button>
        </div>
      </motion.div>

      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="app-card overflow-hidden p-0">
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead>
              <tr className="border-b border-navy-900/10 bg-navy-900 text-white">
                <th className="px-3 py-3 font-semibold">
                  <input type="checkbox" aria-label="Select all rows" onChange={(e) => setSelectedIds(e.target.checked ? items.map((item) => item.id) : [])} checked={items.length > 0 && selectedIds.length === items.length} />
                </th>
                <th className="px-3 py-3 font-semibold">Claim ID</th>
                <th className="px-3 py-3 font-semibold">Policy</th>
                <th className="px-3 py-3 font-semibold">Amount</th>
                <th className="px-3 py-3 font-semibold">Date</th>
                <th className="px-3 py-3 font-semibold">Fraud Score</th>
                <th className="px-3 py-3 font-semibold">Status</th>
              </tr>
            </thead>
            <tbody>
              {items.map((claim) => (
                <tr key={claim.id} className="cursor-pointer border-b border-slate-100 transition hover:bg-navy-50/60" onClick={() => navigate(`/claims/${claim.id}`)}>
                  <td className="px-3 py-2" onClick={(e) => e.stopPropagation()}>
                    <input type="checkbox" aria-label={`Select claim ${claim.id}`} checked={selectedIds.includes(claim.id)} onChange={() => toggleSelect(claim.id)} />
                  </td>
                  <td className="px-3 py-2">{claim.id}</td>
                  <td className="px-3 py-2">{claim.policy_number}</td>
                  <td className="px-3 py-2">{formatCurrency(claim.claim_amount)}</td>
                  <td className="px-3 py-2">{formatDate(claim.accident_date)}</td>
                  <td className="px-3 py-2">
                    <span className={`inline-flex rounded-full px-2 py-1 text-xs font-semibold text-white ${FRAUD_BADGE_CLASS[getFraudScoreVariant(claim.fraud_score || 0)]}`}>
                      {(claim.fraud_score || 0).toFixed(3)}
                    </span>
                  </td>
                  <td className="px-3 py-2">{claim.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="p-4">
          <Pagination
            page={claims.page}
            pageSize={claims.pageSize}
            total={claims.data?.total || 0}
            onPageChange={claims.setPage}
            onPageSizeChange={(size) => {
              claims.setPageSize(size);
              claims.setPage(1);
            }}
          />
        </div>
      </motion.div>

      <ConfirmationModal id="claim-delete-confirm" title="Delete Claim" message="Are you sure you want to delete this claim?" onConfirm={async () => {
        if (selectedIds.length !== 1) return;
        await claimsApi.remove(selectedIds[0]);
        setSelectedIds([]);
        claims.refetch();
      }} confirmLabel="Delete" />
    </section>
  );
}

export default Claims;
