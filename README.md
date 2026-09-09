# CherukadAI Platform

CherukadAI is a multi-tenant AI orchestration platform built as a modular monolith.

## Repository Layout

- `backend/` - FastAPI API, domain modules, SQLAlchemy models, Alembic migrations, and Celery workers.
- `frontend/` - Next.js application using React, TypeScript, Tailwind, and shared UI components.
- `docker-compose.yml` - PostgreSQL, Redis, API, worker, and frontend services.
- `ARCHITECTURE.md` - Platform architecture and design boundaries.

## Configuration

Copy the example environment file and provide local values:

```text
.env.example -> .env
```

Never commit `.env` files or provider credentials. Only example configuration files are tracked.

## Run With Docker Compose

```bash
docker compose up --build
```

The services are available at:

- Frontend: http://localhost:3000
- API: http://localhost:8000
- API documentation: http://localhost:8000/api/v1/docs

Apply database migrations when starting an existing local database:

```bash
cd backend
alembic upgrade head
```

## Run Locally

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
alembic upgrade head
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Tests

Backend tests:

```bash
cd backend
pytest
```

Frontend tests and lint:

```bash
cd frontend
npm test
npm run lint
```
