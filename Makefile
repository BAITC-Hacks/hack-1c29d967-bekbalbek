.DEFAULT_GOAL := help
BACKEND := backend
FRONTEND := frontend

help: ## Show targets
	@grep -E '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

up: ## Start PostgreSQL (docker compose)
	docker compose up -d db
	@until docker compose exec -T db pg_isready -U agent -d agent_workspace >/dev/null 2>&1; do sleep 1; done; echo "db ready"

down: ## Stop containers (data volume is kept)
	docker compose down

stack: ## Build and run the whole stack in Docker (db + api + web) on http://localhost:8080
	docker compose --profile app up --build -d
	@for i in $$(seq 1 120); do curl -sf http://localhost:8080/api/health >/dev/null 2>&1 && break; sleep 1; done; \
	curl -sf http://localhost:8080/api/health >/dev/null 2>&1 || { echo "stack not healthy after 120s; run: docker compose --profile app logs api web"; exit 1; }; \
	echo "stack ready: http://localhost:8080"

stack-down: ## Stop the whole stack (data volume is kept)
	docker compose --profile app down

install: ## Install backend dependencies
	cd $(BACKEND) && uv sync

migrate: ## Apply database migrations
	cd $(BACKEND) && uv run alembic upgrade head

seed: ## Load / reset the sample dataset
	cd $(BACKEND) && uv run python -m scripts.seed

api: ## Run the FastAPI backend on :8000
	cd $(BACKEND) && uv run uvicorn app.main:app --reload --port 8000

api-demo: ## Run the backend without auto-reload (a file save cannot interrupt a live run)
	cd $(BACKEND) && uv run uvicorn app.main:app --port 8000

demo-offline: ## Backend in deterministic scripted mode, no API key needed (run 'make web' in another terminal)
	cd $(BACKEND) && OPENAI_MODEL=scripted:auto uv run uvicorn app.main:app --port 8000

test: ## Backend tests (unit + DB integration; needs the DB)
	cd $(BACKEND) && uv run pytest -q

smoke: ## Walk the whole API flow with curl against a running backend
	cd $(BACKEND) && ./scripts/smoke.sh

eval: ## Run the evaluation suite (scripted model by default; EVAL_MODEL=live uses the real model)
	cd $(BACKEND) && uv run python -m evals.runner

web-install: ## Install frontend dependencies (pnpm)
	cd $(FRONTEND) && pnpm install

web: ## Run the Vite dev server on :5173 (proxies /api to :8000)
	cd $(FRONTEND) && pnpm dev

web-build: ## Type-check and build the frontend into frontend/dist
	cd $(FRONTEND) && pnpm build

test-web: ## Frontend unit tests (vitest)
	cd $(FRONTEND) && pnpm test

e2e: ## Frontend end-to-end flow (needs 'make api' and 'make web' running)
	cd $(FRONTEND) && pnpm test:e2e

lint: ## Lint backend and frontend
	cd $(BACKEND) && uv run ruff check .
	cd $(FRONTEND) && pnpm lint

demo: up migrate seed ## One-shot: db up, migrate, seed
	@echo "Now run 'make api' in one terminal and 'make web' in another, then open http://localhost:5173"
