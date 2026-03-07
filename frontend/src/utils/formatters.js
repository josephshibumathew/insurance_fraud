export function formatDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return new Intl.DateTimeFormat(undefined, { year: "numeric", month: "short", day: "2-digit" }).format(date);
}

export function formatCurrency(value, currency = "USD") {
  if (value == null || Number.isNaN(Number(value))) return "-";
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(Number(value));
}

export function getFraudScoreVariant(score) {
  const numeric = Number(score || 0);
  if (numeric >= 0.7) return "danger";
  if (numeric >= 0.35) return "warning";
  return "success";
}

export function getFraudScoreLabel(score) {
  const numeric = Number(score || 0);
  if (numeric >= 0.7) return "High";
  if (numeric >= 0.35) return "Medium";
  return "Low";
}
