const FEATURE_LABELS = {
  claim_amount: "Claim Amount",
  driver_age: "Driver Age",
  vehicle_age: "Vehicle Age",
  previous_claims: "Previous Claims",
  driver_experience_years: "Driver Experience (Years)",
  policy_type_encoded: "Policy Type",
  policy_pattern: "Policy Pattern",
  accident_recency: "Accident Recency",
  witness: "Witness Present",
  police_report: "Police Report Filed",
};

export function toFeatureLabel(feature) {
  if (!feature) return "Unknown Feature";

  if (feature.startsWith("policy_type_")) {
    const policy = feature.replace("policy_type_", "").replaceAll("_", " ");
    return `Policy Type: ${policy}`;
  }

  if (FEATURE_LABELS[feature]) return FEATURE_LABELS[feature];

  return feature
    .replaceAll("_", " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

export function normalizeShapValues(shapValues = {}) {
  return Object.entries(shapValues)
    .map(([feature, value]) => ({
      feature,
      label: toFeatureLabel(feature),
      value: Number(value) || 0,
    }))
    .sort((a, b) => Math.abs(b.value) - Math.abs(a.value));
}

export function summarizeShapFactors(normalized = []) {
  const increasing = normalized.filter((item) => item.value > 0).slice(0, 3).map((item) => item.label);
  const decreasing = normalized.filter((item) => item.value < 0).slice(0, 3).map((item) => item.label);

  return {
    increasing: increasing.length ? increasing : ["No significant increasing factors"],
    decreasing: decreasing.length ? decreasing : ["No significant decreasing factors"],
  };
}
