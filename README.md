# Automobile Insurance Fraud Detection System

[![CI/CD Pipeline](https://github.com/josephshibumathew/insurance_fraud/actions/workflows/ci.yml/badge.svg)](https://github.com/josephshibumathew/insurance_fraud/actions/workflows/ci.yml)

An end-to-end AI-powered platform for detecting automobile insurance fraud using ensemble machine learning, damage analysis, and AI-generated claim reports.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Tailwind CSS, Recharts |
| Backend API | FastAPI, SQLAlchemy, Alembic |
| Database | PostgreSQL (Supabase in production) |
| ML | Hugging Face Spaces (fraud + damage endpoints) |
| Infra | Docker, Docker Compose, GitHub Actions |

## Production-style Local Stack (Docker)

1. Copy environment template:

```bash
cp .env.example .env.prod
```

2. Update required values in `.env.prod`.

3. Run the full stack:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

4. Access services:
- Frontend: http://localhost
- Backend API: http://localhost:8000
- Backend Health: http://localhost:8000/health
- API docs: http://localhost:8000/docs

5. Stop services:

```bash
docker compose -f docker-compose.prod.yml down
```

## CI/CD Pipeline

Workflow: `.github/workflows/ci.yml`

On pushes to `main` and `develop` (and PRs), the pipeline:
- runs backend tests with Python
- runs frontend tests with Node
- builds backend/frontend Docker images
- runs Trivy filesystem scans on Docker contexts
- pushes images to GHCR when branch is `main`

## Image Publishing

Images are published to GHCR on `main`:
- `ghcr.io/<owner>/insurance-fraud-backend:latest`
- `ghcr.io/<owner>/insurance-fraud-frontend:latest`
- plus short-SHA tags for traceability

## Deployment Notes

- Existing production deployment remains:
	- Frontend: Vercel
	- Backend: Render
	- DB: Supabase
	- ML: Hugging Face Spaces
- Docker and CI/CD additions are focused on build consistency and automated validation.

## Full Deployment Guide

Detailed Docker and CI/CD setup steps are in [deployment.md](deployment.md).

## License

MIT — see [LICENSE](LICENSE)
