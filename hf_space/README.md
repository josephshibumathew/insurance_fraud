---
title: Insurance Fraud ML API
emoji: 🚗
colorFrom: gray
colorTo: yellow
sdk: docker
pinned: false
license: mit
---

# Insurance Fraud ML API

FastAPI inference server for the Automobile Insurance Fraud Detection System.

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Liveness check |
| GET | `/docs` | Interactive Swagger UI |
| POST | `/predict/fraud` | Fraud score + SHAP values from claim data |
| POST | `/predict/damage` | Bounding boxes + severity from a damage image |

## `/predict/fraud` — Request body

```json
{
  "policy_type": "Comprehensive",
  "claim_amount": 15000,
  "accident_date": "2024-03-10",
  "accident_location": "Urban",
  "vehicle_age": 4,
  "vehicle_make": "Honda",
  "vehicle_model": "Civic",
  "driver_age": 32,
  "driver_experience_years": 8,
  "previous_claims": 1,
  "witness": "No",
  "police_report": "Yes"
}
```

## `/predict/damage` — multipart/form-data

Upload a JPEG/PNG image as `image` field.
