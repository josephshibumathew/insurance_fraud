import React, { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { zodResolver } from "@hookform/resolvers/zod";
import { motion } from "framer-motion";
import { useDropzone } from "react-dropzone";
import { useForm } from "react-hook-form";
import { toast } from "react-toastify";
import { z } from "zod";

import ErrorAlert from "../components/common/ErrorAlert";
import { claimsApi } from "../services/api";
import { saveClaimExtendedFields } from "../utils/claimFieldStore";

const schema = z.object({
  policy_number: z.string().min(3, "Policy number is required"),
  policy_type: z.enum(["Comprehensive", "Third Party", "Collision", "Liability"]),
  claim_amount: z.coerce
    .number()
    .min(500, "Claim amount must be at least 500")
    .max(1000000, "Claim amount must be at most 1,000,000"),
  accident_date: z.string().min(1, "Accident date is required"),
  accident_location: z.string().min(2, "Accident location is required"),
  vehicle_age: z.coerce.number().min(0).max(40),
  vehicle_make: z.string().min(2),
  vehicle_model: z.string().min(1),
  driver_age: z.coerce.number().min(18).max(80),
  driver_experience_years: z.coerce.number().min(0).max(80),
  previous_claims: z.coerce.number().min(0).max(20),
  witness: z.enum(["Yes", "No"]),
  police_report: z.enum(["Yes", "No"]),
});

const STEP_LABELS = ["Claim Profile", "Images", "Review"];

function formatDateYYYYMMDD(date = new Date()) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function classifyFraudRisk(fraudScore) {
  if (fraudScore > 70) return "HIGH FRAUD 🔴";
  if (fraudScore > 30) return "SUSPICIOUS 🟡";
  return "SAFE 🟢";
}

function validateBusinessRules(payload) {
  const errors = [];
  const factors = [];
  let fraudScore = 0;

  const todayString = formatDateYYYYMMDD();

  const claimAmount = Number(payload.claim_amount);
  const vehicleAge = Number(payload.vehicle_age);
  const driverAge = Number(payload.driver_age);
  const driverExperienceYears = Number(payload.driver_experience_years);
  const previousClaims = Number(payload.previous_claims);

  if (payload.accident_date && payload.accident_date > todayString) {
    errors.push("Accident date cannot be in the future");
    factors.push("+50: Accident date is in the future");
    fraudScore += 50;
  }

  if (Number.isFinite(vehicleAge) && vehicleAge > 30) {
    errors.push("Vehicle age exceeds realistic limit");
    factors.push("+20: Vehicle age > 30");
    fraudScore += 20;
  }

  if (
    Number.isFinite(driverExperienceYears) &&
    Number.isFinite(driverAge) &&
    driverExperienceYears > driverAge - 18
  ) {
    errors.push("Driver experience is invalid");
    factors.push("+20: Driver experience exceeds allowed maximum");
    fraudScore += 20;
  }

  if (Number.isFinite(claimAmount) && claimAmount > 500000) {
    factors.push("+20: Claim amount > 500,000");
    fraudScore += 20;
  }

  if (Number.isFinite(previousClaims) && previousClaims > 5) {
    errors.push("Too many previous claims (fraud risk)");
    factors.push("+30: Previous claims > 5");
    fraudScore += 30;
  }

  if (payload.police_report === "No" && Number.isFinite(claimAmount) && claimAmount > 50000) {
    errors.push("High claim without police report");
    factors.push("+25: Claim > 50,000 with no police report");
    fraudScore += 25;
  }

  const riskLevel = classifyFraudRisk(fraudScore);
  return { errors, fraudScore, riskLevel, factors };
}

function parseCsvLine(line = "") {
  const values = [];
  let current = "";
  let inQuotes = false;

  for (let index = 0; index < line.length; index += 1) {
    const char = line[index];
    if (char === '"') {
      if (inQuotes && line[index + 1] === '"') {
        current += '"';
        index += 1;
      } else {
        inQuotes = !inQuotes;
      }
      continue;
    }
    if (char === "," && !inQuotes) {
      values.push(current.trim());
      current = "";
      continue;
    }
    current += char;
  }

  values.push(current.trim());
  return values;
}

function toYesNo(value, defaultValue = "No") {
  if (!value) return defaultValue;
  const normalized = String(value).trim().toLowerCase();
  return ["yes", "y", "true", "1"].includes(normalized) ? "Yes" : "No";
}

function normalizePolicyType(value, defaultValue = "Comprehensive") {
  if (!value) return defaultValue;
  const normalized = String(value).trim().toLowerCase();
  if (normalized.includes("third")) return "Third Party";
  if (normalized.includes("collision")) return "Collision";
  if (normalized.includes("liability")) return "Liability";
  return "Comprehensive";
}

function NewClaim() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [fraudResult, setFraudResult] = useState(null);
  const [files, setFiles] = useState([]);
  const [csvFile, setCsvFile] = useState(null);

  const todayString = formatDateYYYYMMDD();

  const {
    register,
    handleSubmit,
    trigger,
    setValue,
    watch,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(schema),
    defaultValues: {
      policy_number: "",
      policy_type: "Comprehensive",
      claim_amount: "",
      accident_date: "",
      accident_location: "",
      vehicle_age: "",
      vehicle_make: "",
      vehicle_model: "",
      driver_age: "",
      driver_experience_years: "",
      previous_claims: 0,
      witness: "No",
      police_report: "No",
    },
  });

  const values = watch();

  const onDrop = (acceptedFiles) => {
    setFiles(acceptedFiles);
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "image/*": [] },
    multiple: true,
  });

  const previews = useMemo(
    () => files.map((file) => ({ file, url: URL.createObjectURL(file) })),
    [files]
  );

  const nextStep = async () => {
    if (step === 0) {
      const valid = await trigger();
      if (!valid) return;
    }
    setStep((prev) => Math.min(prev + 1, STEP_LABELS.length - 1));
  };

  const previousStep = () => setStep((prev) => Math.max(prev - 1, 0));

  const onSubmit = async (payload) => {
    setError("");
    const businessRulesResult = validateBusinessRules(payload);
    setFraudResult(businessRulesResult);

    if (businessRulesResult.errors.length > 0) {
      setError(businessRulesResult.errors.join(" | "));
      return;
    }

    setSubmitting(true);

    try {
      const formData = new FormData();
      formData.append("policy_number", payload.policy_number);
      formData.append("claim_amount", String(payload.claim_amount));
      formData.append("accident_date", payload.accident_date);

      const { data } = await claimsApi.createWithForm(formData);
      const claimId = data.id;

      saveClaimExtendedFields(claimId, payload);

      for (const image of files) {
        const imageData = new FormData();
        imageData.append("image_file", image);
        await claimsApi.uploadImage(claimId, imageData);
      }

      toast.success("Claim submitted successfully");
      navigate(`/claims/${claimId}`);
    } catch (submitError) {
      const message = submitError.response?.data?.detail || "Failed to submit claim";
      setError(message);
      toast.error(message);
    } finally {
      setSubmitting(false);
      previews.forEach((preview) => URL.revokeObjectURL(preview.url));
    }
  };

  return (
    <section className="space-y-4">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="page-title">New Claim Intake</h1>
        <span className="app-badge app-badge-navy">Step {step + 1} / {STEP_LABELS.length}</span>
      </div>

      {/* Step progress bar */}
      <div className="flex items-center gap-2">
        {STEP_LABELS.map((label, idx) => (
          <React.Fragment key={label}>
            <div className="flex items-center gap-1.5">
              <div className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-semibold transition-colors ${
                idx <= step ? "bg-navy-900 text-white" : "bg-slate-200 text-slate-500"
              }`}>
                {idx + 1}
              </div>
              <span className={`hidden text-sm sm:inline ${idx <= step ? "text-navy-900 font-medium" : "text-slate-400"}`}>{label}</span>
            </div>
            {idx < STEP_LABELS.length - 1 && (
              <div className={`h-0.5 flex-1 transition-colors ${idx < step ? "bg-navy-900" : "bg-slate-200"}`} />
            )}
          </React.Fragment>
        ))}
      </div>

      {error && <ErrorAlert message={error} onClose={() => setError("")} />}

      <form onSubmit={handleSubmit(onSubmit)}>
        <div className="mb-4 rounded-xl border border-slate-200 bg-white p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-sm font-semibold text-slate-700">Fraud Score: <span className="text-slate-900">{fraudResult?.fraudScore ?? 0}</span></p>
            <p className="text-sm font-semibold text-slate-700">Risk Level: <span className="text-slate-900">{fraudResult?.riskLevel ?? "SAFE 🟢"}</span></p>
          </div>

          {fraudResult?.factors?.length ? (
            <div className="mt-2">
              <p className="text-xs font-semibold text-slate-500">Score factors</p>
              <p className="mt-1 text-xs text-slate-600">{fraudResult.factors.join(" • ")}</p>
            </div>
          ) : null}
        </div>
        

        <motion.div
          key={step}
          className="app-card"
          initial={{ opacity: 0, x: 10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.2 }}
        >
          {step === 0 && (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {/* CSV upload — full width */}
              <div className="sm:col-span-2 lg:col-span-4">
                <label className="form-label-tw">Optional CSV Upload</label>
                <input
                  type="file"
                  accept=".csv"
                  className="app-input"
                  onChange={async (event) => {
                    const selectedFile = event.target.files?.[0] || null;
                    setCsvFile(selectedFile);
                    if (!selectedFile) return;

                    try {
                      const text = await selectedFile.text();
                      const lines = text
                        .split(/\r?\n/)
                        .map((line) => line.trim())
                        .filter(Boolean);

                      if (lines.length < 2) {
                        toast.error("CSV must include headers and at least one data row");
                        return;
                      }

                      const headers = parseCsvLine(lines[0]).map((header) => header.toLowerCase().trim());
                      const firstRow = parseCsvLine(lines[1]);
                      const row = {};
                      headers.forEach((header, idx) => {
                        row[header] = firstRow[idx] ?? "";
                      });

                      const getValue = (...keys) => {
                        for (const key of keys) {
                          const normalized = key.toLowerCase();
                          if (row[normalized] !== undefined && row[normalized] !== "") {
                            return row[normalized];
                          }
                        }
                        return "";
                      };

                      setValue("policy_number", getValue("policy_number", "policy no", "policy"));
                      setValue("policy_type", normalizePolicyType(getValue("policy_type", "policy type")));
                      setValue("claim_amount", Number(getValue("claim_amount", "claim amount")) || "");
                      setValue("accident_date", getValue("accident_date", "accident date", "date_of_accident"));
                      setValue("accident_location", getValue("accident_location", "accident location", "location"));
                      setValue("vehicle_age", Number(getValue("vehicle_age", "vehicle age")) || 0);
                      setValue("vehicle_make", getValue("vehicle_make", "vehicle make", "make"));
                      setValue("vehicle_model", getValue("vehicle_model", "vehicle model", "model"));
                      setValue("driver_age", Number(getValue("driver_age", "driver age")) || 18);
                      setValue("driver_experience_years", Number(getValue("driver_experience_years", "driver_experience", "experience_years")) || 0);
                      setValue("previous_claims", Number(getValue("previous_claims", "previous claims", "past_claims")) || 0);
                      setValue("witness", toYesNo(getValue("witness", "has_witness")));
                      setValue("police_report", toYesNo(getValue("police_report", "police report", "has_police_report")));

                      toast.success("CSV parsed and form auto-filled");
                    } catch (_error) {
                      toast.error("Unable to parse CSV file");
                    }
                  }}
                />
                <p className="mt-1 text-xs text-slate-500">Uploading CSV will auto-fill claim fields from the first data row. You can edit values before submitting.</p>
              </div>

              {/* Policy Number */}
              <div className="sm:col-span-1 lg:col-span-2">
                <label className="form-label-tw">Policy Number</label>
                <input className="app-input" {...register("policy_number")} />
                {errors.policy_number && <p className="form-error-tw">{errors.policy_number.message}</p>}
              </div>

              {/* Policy Type */}
              <div className="sm:col-span-1 lg:col-span-2">
                <label className="form-label-tw">Policy Type</label>
                <select className="app-input" {...register("policy_type")}>
                  <option value="Comprehensive">Comprehensive</option>
                  <option value="Third Party">Third Party</option>
                  <option value="Collision">Collision</option>
                  <option value="Liability">Liability</option>
                </select>
              </div>

              {/* Claim Amount */}
              <div>
                <label className="form-label-tw">Claim Amount</label>
                <input type="number" className="app-input" step="0.01" {...register("claim_amount")} />
              </div>

              {/* Accident Date */}
              <div>
                <label className="form-label-tw">Accident Date</label>
                <input type="date" className="app-input" max={todayString} {...register("accident_date")} />
              </div>

              {/* Accident Location */}
              <div className="sm:col-span-2">
                <label className="form-label-tw">Accident Location</label>
                <input className="app-input" {...register("accident_location")} />
              </div>

              {/* Vehicle Age */}
              <div>
                <label className="form-label-tw">Vehicle Age</label>
                <input type="number" className="app-input" {...register("vehicle_age")} />
              </div>

              {/* Vehicle Make */}
              <div>
                <label className="form-label-tw">Vehicle Make</label>
                <input className="app-input" {...register("vehicle_make")} />
              </div>

              {/* Vehicle Model */}
              <div>
                <label className="form-label-tw">Vehicle Model</label>
                <input className="app-input" {...register("vehicle_model")} />
              </div>

              {/* Previous Claims */}
              <div>
                <label className="form-label-tw">Previous Claims</label>
                <input type="number" className="app-input" {...register("previous_claims")} />
              </div>

              {/* Driver Age */}
              <div>
                <label className="form-label-tw">Driver Age</label>
                <input type="number" className="app-input" {...register("driver_age")} />
              </div>

              {/* Driver Experience */}
              <div className="sm:col-span-1 lg:col-span-2">
                <label className="form-label-tw">Driver Experience (Years)</label>
                <input type="number" className="app-input" {...register("driver_experience_years")} />
              </div>

              {/* Witness */}
              <div>
                <label className="form-label-tw">Witness</label>
                <select className="app-input" {...register("witness")}>
                  <option value="Yes">Yes</option>
                  <option value="No">No</option>
                </select>
              </div>

              {/* Police Report */}
              <div>
                <label className="form-label-tw">Police Report</label>
                <select className="app-input" {...register("police_report")}>
                  <option value="Yes">Yes</option>
                  <option value="No">No</option>
                </select>
              </div>
            </div>
          )}

          {step === 1 && (
            <div className="space-y-4">
              <h2 className="text-base font-semibold text-slate-900">Upload Damage Images</h2>
              <div {...getRootProps({ className: `dropzone ${isDragActive ? "active" : ""}` })}>
                <input {...getInputProps()} />
                <p className="mb-1 font-semibold text-slate-700">Drag and drop images here</p>
                <p className="text-sm text-slate-500">or click to select files</p>
              </div>

              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                {previews.map((preview) => (
                  <div key={preview.file.name} className="overflow-hidden rounded-xl border border-slate-200 bg-white">
                    <img src={preview.url} alt={preview.file.name} className="w-full object-cover" />
                    <p className="truncate px-2 py-1 text-xs text-slate-500">{preview.file.name}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-4">
              <h2 className="text-base font-semibold text-slate-900">Review Before Submission</h2>
              {csvFile && <p className="text-sm text-slate-500">CSV source: <span className="font-medium text-slate-700">{csvFile.name}</span></p>}
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
                {Object.entries(values).map(([key, value]) => (
                  <div key={key} className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                    <p className="mb-0.5 text-xs font-medium uppercase tracking-wide text-slate-400">{key.replaceAll("_", " ")}</p>
                    <p className="font-semibold text-slate-800">{String(value || "-")}</p>
                  </div>
                ))}
              </div>
              <p className="text-sm text-slate-500">Images selected: <span className="font-medium text-slate-700">{files.length}</span></p>
            </div>
          )}

          <div className="mt-6 flex justify-between">
            <button
              type="button"
              className="app-button-secondary"
              onClick={previousStep}
              disabled={step === 0 || submitting}
            >
              Back
            </button>

            {step < STEP_LABELS.length - 1 ? (
              <button type="button" className="app-button" onClick={nextStep}>
                Continue
              </button>
            ) : (
              <button type="submit" className="app-button" disabled={submitting}>
                {submitting ? "Submitting…" : "Submit Claim"}
              </button>
            )}
          </div>
        </motion.div>
      </form>
    </section>
  );
}

export default NewClaim;
