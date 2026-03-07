# Deployment Guide (Docker + CI/CD)

This guide explains how to run a production-like stack locally with Docker and how CI/CD is configured with GitHub Actions.

## 1) Required Files

- `backend/Dockerfile.prod`
- `backend/scripts/entrypoint.prod.sh`
- `frontend/Dockerfile.prod`
- `frontend/nginx/default.conf`
- `docker-compose.prod.yml`
- `.env.example`, `.env.dev`, `.env.staging`, `.env.prod`
- `.github/workflows/ci.yml`

## 2) Environment Setup

Use `.env.example` as your source of truth, then copy values into the environment you need:

```bash
cp .env.example .env.prod
```

Variables you must set for production-like runs:

- `DATABASE_URL`
- `JWT_SECRET_KEY`
- `GROQ_API_KEY`
- `BACKEND_CORS_ORIGINS`
- `ML_API_URL`
- `FRONTEND_API_URL`

For real production, inject secrets from your platform runtime environment instead of storing actual secrets in git-tracked files.

## 3) Build and Run Locally

Run full stack:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
```

Check status:

```bash
docker compose -f docker-compose.prod.yml ps
```

Stop stack:

```bash
docker compose -f docker-compose.prod.yml down
```

## 4) Service Endpoints

- Frontend: `http://localhost`
- Backend: `http://localhost:8000`
- Health: `http://localhost:8000/health`
- API Docs: `http://localhost:8000/docs`

## 5) Database Migrations

`backend/scripts/entrypoint.prod.sh` runs:

```bash
alembic upgrade head
```

before starting Gunicorn when `RUN_MIGRATIONS=true`.

## 6) ML Handling

For local production simulation, compose starts `ml-mock` (`ml-service/mock_api.py`).

- Set `ML_API_URL=http://ml-mock:7860` to use mock predictions.
- For real model inference, set `ML_API_URL` to your Hugging Face Space URL.

## 7) CI/CD Workflow

Workflow file: `.github/workflows/ci.yml`

Triggers:
- push on `main`, `develop`
- pull requests targeting `main`, `develop`

Jobs:
- `test-backend`: installs backend dependencies and runs `pytest backend/tests`
- `test-frontend`: installs frontend dependencies and runs `npm test`
- `build-docker`: builds backend/frontend images, scans contexts with Trivy, and pushes images on `main`

## 8) Container Registry

Current workflow publishes to GitHub Container Registry (GHCR):

- `ghcr.io/<owner>/insurance-fraud-backend`
- `ghcr.io/<owner>/insurance-fraud-frontend`

Tags include:
- `latest` (default branch)
- short commit SHA

## 9) Existing Hosted Deployment

Your existing free-tier deployment model remains valid:

- Frontend: Vercel
- Backend: Render
- Database: Supabase
- ML API: Hugging Face Spaces

Docker and CI/CD in this guide are added for consistency, reproducibility, and automation.