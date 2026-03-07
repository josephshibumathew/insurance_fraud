import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";

import { adminApi } from "../services/api";
import LoadingSpinner from "../components/common/LoadingSpinner";
import ErrorAlert from "../components/common/ErrorAlert";
import Pagination from "../components/common/Pagination";
import { formatCurrency, formatDate } from "../utils/formatters";

function AdminClaims() {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  const claimsQuery = useQuery({
    queryKey: ["admin", "claims", page, pageSize],
    queryFn: async () => (await adminApi.claims({ page, page_size: pageSize })).data,
  });

  if (claimsQuery.isLoading) return <LoadingSpinner text="Loading claims..." />;

  return (
    <section className="space-y-3">
      <h1 className="page-title">All Claims</h1>
      {claimsQuery.error ? <ErrorAlert message={claimsQuery.error.message || "Failed to load claims"} /> : null}

      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="app-card overflow-hidden p-0">
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead>
              <tr className="bg-navy-900 text-white">
                <th className="px-3 py-2">ID</th>
                <th className="px-3 py-2">User ID</th>
                <th className="px-3 py-2">Policy</th>
                <th className="px-3 py-2">Amount</th>
                <th className="px-3 py-2">Accident Date</th>
                <th className="px-3 py-2">Fraud Score</th>
                <th className="px-3 py-2">Status</th>
              </tr>
            </thead>
            <tbody>
              {(claimsQuery.data?.items || []).map((claim) => (
                <tr key={claim.id} className="border-b border-slate-100 last:border-none">
                  <td className="px-3 py-2">{claim.id}</td>
                  <td className="px-3 py-2">{claim.user_id}</td>
                  <td className="px-3 py-2">{claim.policy_number}</td>
                  <td className="px-3 py-2">{formatCurrency(claim.claim_amount)}</td>
                  <td className="px-3 py-2">{formatDate(claim.accident_date)}</td>
                  <td className="px-3 py-2">{claim.fraud_score != null ? Number(claim.fraud_score).toFixed(3) : "-"}</td>
                  <td className="px-3 py-2">{claim.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="p-4">
          <Pagination
            page={page}
            pageSize={pageSize}
            total={claimsQuery.data?.total || 0}
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

export default AdminClaims;
