import React, { useMemo } from "react";
import { format } from "date-fns";
import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { formatCurrency, getFraudScoreLabel, getFraudScoreVariant } from "../../utils/formatters";
import { normalizeShapValues, summarizeShapFactors } from "../../utils/shap";

function InfoRow({ label, value }) {
  return (
    <tr>
      <th className="text-muted fw-semibold" style={{ width: "35%" }}>{label}</th>
      <td>{value ?? "-"}</td>
    </tr>
  );
}

function ReportPreview({ claim, extendedFields, fraud, images, reportId, onDownload }) {
  const normalizedShap = useMemo(() => normalizeShapValues(fraud?.shap_values || {}), [fraud]);
  const shapSummary = useMemo(() => summarizeShapFactors(normalizedShap), [normalizedShap]);
  const fraudScore = Number(fraud?.fusion_score ?? fraud?.ensemble_score ?? claim?.fraud_score ?? 0);
  const reportDate = format(new Date(), "PPpp");

  const recommendation = fraudScore >= 0.7 ? "Recommended: Denial / Deep investigation"
    : fraudScore >= 0.35 ? "Recommended: Manual review by senior surveyor"
      : "Recommended: Approve with standard checks";

  const narrative = `The claim shows a ${getFraudScoreLabel(fraudScore).toLowerCase()} fraud risk profile based on model analysis. Key risk drivers include ${shapSummary.increasing.join(", ")} while mitigating factors include ${shapSummary.decreasing.join(", ")}.`;

  return (
    <div className="card card-body soft-gradient">
      <div className="d-flex flex-wrap justify-content-between gap-2 mb-3">
        <div>
          <h2 className="h5 mb-1">Fraud Assessment Report</h2>
          <div className="text-muted small">Claim #{claim?.id} · Generated {reportDate}</div>
        </div>
        <div className="d-flex align-items-center gap-2">
          <span className={`badge text-bg-${getFraudScoreVariant(fraudScore)} px-3 py-2`}>
            Fraud Score: {(fraudScore * 100).toFixed(1)}%
          </span>
          <button className="btn btn-primary btn-sm" onClick={onDownload} disabled={!reportId}>
            Download PDF
          </button>
        </div>
      </div>

      <div className="row g-3">
        <div className="col-12 col-xl-6">
          <div className="card card-body h-100">
            <h3 className="h6">Claim Summary Table</h3>
            <div className="table-responsive">
              <table className="table table-sm mb-0">
                <tbody>
                  <InfoRow label="Policy Number" value={claim?.policy_number} />
                  <InfoRow label="Policy Type" value={extendedFields?.policy_type} />
                  <InfoRow label="Claim Amount" value={formatCurrency(claim?.claim_amount)} />
                  <InfoRow label="Accident Date" value={claim?.accident_date} />
                  <InfoRow label="Accident Location" value={extendedFields?.accident_location} />
                  <InfoRow label="Vehicle" value={`${extendedFields?.vehicle_make || ""} ${extendedFields?.vehicle_model || ""}`} />
                  <InfoRow label="Vehicle Age" value={extendedFields?.vehicle_age} />
                  <InfoRow label="Driver Age" value={extendedFields?.driver_age} />
                  <InfoRow label="Driver Experience" value={extendedFields?.driver_experience_years} />
                  <InfoRow label="Previous Claims" value={extendedFields?.previous_claims} />
                  <InfoRow label="Witness" value={extendedFields?.witness} />
                  <InfoRow label="Police Report" value={extendedFields?.police_report} />
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div className="col-12 col-xl-6">
          <div className="card card-body h-100">
            <h3 className="h6">Fraud Risk Analysis</h3>
            <p className="mb-2">Risk Level: <span className={`badge text-bg-${getFraudScoreVariant(fraudScore)}`}>{getFraudScoreLabel(fraudScore)}</span></p>
            <p className="mb-2">Confidence: {(Math.abs(fraudScore - 0.5) * 2 * 100).toFixed(1)}%</p>
            <p className="mb-0 text-muted small">Model reference includes claim amount, driver profile, vehicle profile, history, and policy attributes.</p>
          </div>
        </div>

        <div className="col-12 col-xl-6">
          <div className="card card-body h-100">
            <h3 className="h6">SHAP Explanation</h3>
            {normalizedShap.length ? (
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={normalizedShap.slice(0, 10)} layout="vertical" margin={{ left: 8, right: 8 }}>
                  <XAxis type="number" />
                  <YAxis type="category" dataKey="label" width={160} />
                  <Tooltip />
                  <Bar dataKey="value">
                    {normalizedShap.slice(0, 10).map((item) => (
                      <Cell key={item.feature} fill={item.value >= 0 ? "#ef4444" : "#22c55e"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : <p className="text-muted">SHAP values unavailable for this claim.</p>}

            <p className="small mb-1"><strong>Top factors increasing fraud risk:</strong> {shapSummary.increasing.join(", ")}</p>
            <p className="small mb-0"><strong>Top factors decreasing fraud risk:</strong> {shapSummary.decreasing.join(", ")}</p>
          </div>
        </div>

        <div className="col-12 col-xl-6">
          <div className="card card-body h-100">
            <h3 className="h6">Damage Assessment</h3>
            {(images || []).length === 0 ? <p className="text-muted mb-0">No image assessments available.</p> : (
              <div className="d-flex flex-column gap-2">
                {images.map((image) => (
                  <div key={image.id} className="border rounded p-2 bg-light">
                    <div className="fw-semibold">Image #{image.id}</div>
                    <div className="small text-muted">Severity: {image.damage_results?.severity_score ?? "-"}</div>
                    <div className="small text-muted">Affected parts: {(image.damage_results?.affected_parts || []).join(", ") || "-"}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="col-12">
          <div className="card card-body">
            <h3 className="h6">LLM Narrative</h3>
            <blockquote className="blockquote mb-0">
              <p className="small mb-0">{narrative}</p>
            </blockquote>
          </div>
        </div>

        <div className="col-12">
          <div className="card card-body border-primary-subtle">
            <h3 className="h6">Recommendation</h3>
            <p className="mb-0">{recommendation}</p>
          </div>
        </div>

        <div className="col-12">
          <p className="small text-muted mb-0">Disclaimer: This AI-generated report is an analytical aid and must be reviewed by a qualified insurance professional before final adjudication.</p>
        </div>
      </div>
    </div>
  );
}

export default ReportPreview;
