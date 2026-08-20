# Verdict — AI Purchase Decision Engine

AI-powered purchase decision engine. YouCam Virtual Try-On is used as a structural input (try-on renders feed the decision pipeline).

## Monorepo layout

```
verdict/
├── frontend/   # Next.js 14, TypeScript, Tailwind, Firebase Auth
├── backend/    # FastAPI, SQLAlchemy 2.0, Alembic, Firebase Admin
├── docker-compose.yml   # Postgres 16 (local dev)
└── .env        # local secrets (never commit)
```

## Backend

### Run the API

```bash
cd backend
.venv\Scripts\python -m uvicorn verdict_backend.main:app --reload
```

### Database (Postgres)

Start the database:

```bash
docker compose up -d postgres
```

Run migrations:

```bash
cd backend
.venv\Scripts\alembic upgrade head
```

### Verify the schema

Fast check with `psql` (inside the container):

```bash
docker exec -it verdict-postgres psql -U verdict -d verdict -c "\dt"
```

Or run the automated verification script (checks tables, columns, FKs,
the one-to-one constraint on `garment_attributes`, and does a cleaned-up
round-trip insert):

```bash
cd backend
.venv\Scripts\python scripts\test_schema.py
```

Expected output ends with `Schema verification PASSED` and the following tables:

```
users, wardrobe_items, garment_attributes, decision_logs, alembic_version
```

### Adding a new migration

```bash
cd backend
.venv\Scripts\alembic revision --autogenerate -m "describe change"
.venv\Scripts\alembic upgrade head
```
