.PHONY: install install-backend install-frontend dev dev-backend dev-frontend lint lint-backend lint-frontend format format-backend format-frontend test-db test-cloudinary test-chromadb test-infra

# ── Install dependencies ──────────────────────

install: install-backend install-frontend

install-backend:
	cd backend && python -m venv .venv && .venv\Scripts\activate && pip install -r requirements.txt

install-frontend:
	cd frontend && npm install

# ── Run dev servers ───────────────────────────

dev:
	start cmd /c "cd backend && .venv\Scripts\activate && uvicorn verdict_backend.main:app --reload --port 8000"
	start cmd /c "cd frontend && npm run dev"

dev-backend:
	cd backend && .venv\Scripts\activate && uvicorn verdict_backend.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

# ── Lint ──────────────────────────────────────

lint: lint-backend lint-frontend

lint-backend:
	cd backend && .venv\Scripts\activate && ruff check verdict_backend

lint-frontend:
	cd frontend && npm run lint

# ── Format ────────────────────────────────────

format: format-backend format-frontend

format-backend:
	cd backend && .venv\Scripts\activate && black verdict_backend

format-frontend:
	cd frontend && npm run format

# ── Infrastructure tests ─────────────────────

test-db:
	cd backend && .venv\Scripts\activate && python scripts/test_db.py

test-cloudinary:
	cd backend && .venv\Scripts\activate && python scripts/test_cloudinary.py

test-chromadb:
	cd backend && .venv\Scripts\activate && python scripts/test_chromadb.py

test-infra: test-db test-cloudinary test-chromadb
