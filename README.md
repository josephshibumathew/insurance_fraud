# Automobile Insurance Fraud Detection System

An end-to-end AI-powered platform for detecting fraudulent automobile insurance claims using ensemble machine learning, YOLOv11 damage analysis, and Groq LLM-generated reports.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Tailwind CSS, Recharts, Framer Motion |
| Backend API | FastAPI, SQLAlchemy, Alembic, Python 3.11 |
| Database | PostgreSQL (Supabase in production) |
| ML / AI | Ensemble model, YOLOv11 (damage detection), Groq LLM |
| Auth | JWT (access + refresh tokens), RBAC (admin / surveyor) |
| Infra | Docker Compose (local), Render + Vercel + Supabase (production) |

## Features

- **Claim intake** — multi-step form with CSV auto-fill and image upload
- **Fraud scoring** — ensemble model with SHAP explainability
- **Damage analysis** — YOLOv11 object detection with bounding-box visualization
- **AI reports** — Groq LLM-generated PDF reports per claim
- **Admin dashboard** — system-wide stats, surveyor management, live system logs
- **RBAC** — role-gated routes for admin and surveyor roles

## Local Development

### Prerequisites
- Docker & Docker Compose
- Node.js 18+

### Start everything
```bash
docker compose up -d --build
```

Frontend: http://localhost:3000  
Backend API: http://localhost:8000  
API Docs: http://localhost:8000/docs

### Backend only (without Docker)
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in your values
uvicorn app.main:app --reload
```

### Frontend only
```bash
cd frontend
cp .env.example .env
npm install
npm start
```

## Environment Variables

### Backend (`backend/.env`)
| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `JWT_SECRET_KEY` | Random 64-char hex string |
| `GROQ_API_KEY` | From console.groq.com |
| `BACKEND_CORS_ORIGINS` | JSON array of allowed frontend origins |
| `ENVIRONMENT` | `development` or `production` |

### Frontend (`frontend/.env`)
| Variable | Description |
|---|---|
| `REACT_APP_API_URL` | Backend base URL |

## Deployment

See the deployment guide for step-by-step instructions:
- **Database**: Supabase (free PostgreSQL)
- **Backend**: Render (free Web Service)
- **Frontend**: Vercel (free)

## Project Structure

```
backend/          FastAPI application, Alembic migrations
frontend/         React SPA
ml_models/        Training scripts, ensemble, YOLO module
database/         SQL init scripts, seed data
docs/             SRS, SDD, meeting notes, literature review
tests/            Integration, security, performance, ML tests
```

## License

MIT — see [LICENSE](LICENSE)
