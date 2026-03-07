import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { claimsApi } from "../services/api";
import { useAuth } from "../contexts/AuthContext";

function useClaims(initialPageSize = 10) {
  const { user } = useAuth();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(initialPageSize);
  const [search, setSearch] = useState("");
  const [filters, setFilters] = useState({
    status: "",
    minFraudScore: "",
    maxFraudScore: "",
    fromDate: "",
    toDate: "",
  });

  const queryParams = useMemo(
    () => ({
      page,
      page_size: pageSize,
      status: filters.status || undefined,
      policy_number: search || undefined,
    }),
    [page, pageSize, filters.status, search]
  );

  const query = useQuery({
    queryKey: ["claims", user?.id || "anonymous", queryParams],
    queryFn: async () => {
      const { data } = await claimsApi.list(queryParams);
      const items = (data.items || []).filter((item) => {
        if (filters.minFraudScore && (item.fraud_score ?? 0) < Number(filters.minFraudScore)) return false;
        if (filters.maxFraudScore && (item.fraud_score ?? 0) > Number(filters.maxFraudScore)) return false;
        if (filters.fromDate && item.accident_date < filters.fromDate) return false;
        if (filters.toDate && item.accident_date > filters.toDate) return false;
        return true;
      });
      return { ...data, items };
    },
    enabled: Boolean(user?.id),
    keepPreviousData: true,
  });

  return {
    ...query,
    page,
    setPage,
    pageSize,
    setPageSize,
    search,
    setSearch,
    filters,
    setFilters,
  };
}

export default useClaims;
