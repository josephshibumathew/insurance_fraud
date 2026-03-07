# Testing and Optimization Strategy

## 1) Test Pyramid and Coverage Targets
- Unit tests: target >= 80% for core business logic.
- Integration tests: cover critical workflows (auth, claim ingest, fraud prediction, report generation).
- Security tests: baseline OWASP checks (injection, auth bypass, token tampering, upload abuse).
- Performance tests: endpoint SLO checks and regression gates.
- ML tests: CV + ROC/PR + confusion matrix + ablation and SHAP consistency.

## 2) Optimization Plan

### Database Indexing Strategy
- Add and maintain indexes on:
  - `users.email`
  - `claims.policy_number`, `claims.user_id`, `claims.created_at`
  - `fraud_predictions.claim_id`, `fraud_predictions.created_at`
  - `reports.claim_id`, `reports.created_at`
- Validate with query plans (`EXPLAIN`/`EXPLAIN ANALYZE`) and benchmark before/after.

### Redis Caching
- Cache frequent read endpoints:
  - `/dashboard/stats`
  - `/dashboard/trends`
  - `/claims` first pages
- Suggested TTL:
  - dashboard stats: 30s
  - claims list: 60s
- Invalidate cache on claim create/update/delete and prediction/report creation.

### ML Optimization
- Quantization path (if needed): convert CPU inference path to int8 for tabular submodels.
- Preload models at startup to avoid cold starts.
- Batch requests where possible (`/fraud/batch`) to improve throughput.

### Image Pipeline Optimization
- Compress and resize uploads before inference (max dimension cap, quality 80-85).
- Use async/background jobs for heavy image tasks.
- Persist preprocessed tensors/intermediate metadata for repeat access.

### Frontend Optimization
- Route-level lazy loading (already enabled).
- CDN cache headers for static assets.
- Image lazy loading in claim gallery (already enabled).
- Keep payloads small through pagination and selective fields.

## 3) Security Hardening Checklist
- JWT secrets and API keys from environment-only.
- Enforce HTTPS in production.
- Password complexity + lockout policy.
- Strict authorization checks for admin/permissions.
- Sanitize user-visible strings and validate all inputs.
- Audit logs with request IDs.

## 4) Performance Targets (SLO)
- Non-ML endpoints: <100ms median.
- Login verification: <200ms median.
- Token validation: <50ms median.
- Tabular inference: <200ms.
- Image inference: <3s.

## 5) CI/CD Quality Gates
- Run unit + integration + security + ML suites on push to `main`/`develop`.
- Fail if benchmark regression exceeds 20% from baseline.
- Publish coverage artifact and track trends over time.
