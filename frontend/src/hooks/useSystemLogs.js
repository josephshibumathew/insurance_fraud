import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { adminApi } from "../services/api";

function normalizeLevel(level) {
  if (!level) return "INFO";
  const upper = String(level).toUpperCase();
  if (["INFO", "ERROR", "WARNING", "WARN", "DEBUG", "CRITICAL"].includes(upper)) {
    return upper === "WARN" ? "WARNING" : upper;
  }
  return "INFO";
}

function parseLogLine(line, source = "system") {
  const raw = String(line || "");
  const match = raw.match(/^(\d{4}-\d{2}-\d{2}[^|]*)\s*\|\s*([^|]+)\s*\|\s*([A-Za-z]+)\s*\|\s*(.*)$/);

  if (match) {
    return {
      id: `${source}-${match[1]}-${match[4]}`,
      timestamp: match[1].trim(),
      level: normalizeLevel(match[3]),
      message: match[4].trim(),
      source,
      raw,
    };
  }

  return {
    id: `${source}-${raw}`,
    timestamp: "",
    level: "INFO",
    message: raw,
    source,
    raw,
  };
}

function normalizeLogs(payload) {
  if (Array.isArray(payload)) {
    return payload.map((entry, index) => ({
      id: `array-${index}-${entry?.timestamp || ""}-${entry?.message || ""}`,
      timestamp: entry?.timestamp || "",
      level: normalizeLevel(entry?.level),
      message: entry?.message || "",
      source: entry?.source || "system",
      raw: JSON.stringify(entry),
    }));
  }

  const grouped = payload?.logs || {};
  const output = [];

  Object.entries(grouped).forEach(([source, data]) => {
    const lines = Array.isArray(data?.lines) ? data.lines : [];
    lines.forEach((line) => {
      output.push(parseLogLine(line, source));
    });
  });

  return output;
}

export default function useSystemLogs(lines = 200) {
  const query = useQuery({
    queryKey: ["admin", "system-logs", lines],
    queryFn: async () => (await adminApi.logs({ lines })).data,
    refetchInterval: 3000,
    refetchIntervalInBackground: true,
  });

  const entries = useMemo(() => normalizeLogs(query.data), [query.data]);

  return {
    ...query,
    entries,
    surveyors: query.data?.surveyors || [],
    mlModels: query.data?.ml_models || null,
    environment: query.data?.environment || "unknown",
  };
}
