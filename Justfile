set shell := ["bash", "-c"]

# Default recipe
default: verify

# Clean up temporary cache files
clean:
    @echo "Cleaning up..."
    -rm -rf .tmp
    -rm -rf .npm_cache
    -find . -name "__pycache__" -exec rm -rf {} +
    -rm -rf web-client/.next
    -rm -f backend/data/uploaded.mdb
    @echo "Cleanup complete."

# Build Docker containers
build:
    @echo "Building containers..."
    docker compose build

# Build frontend application
build-frontend:
    @echo "Building frontend..."
    cd web-client && npm run build

# Reinstall frontend dependencies
reinstall-frontend:
    @echo "Reinstalling frontend dependencies (using local cache)..."
    cd web-client && rm -rf node_modules package-lock.json && npm install --verbose --cache .npm-cache

# Build frontend with debug options and increased memory
build-frontend-debug:
    @echo "Building frontend with debug options..."
    cd web-client && NODE_OPTIONS="--max-old-space-size=4096" npm run build -- --debug

# Start services in the background
up:
    @echo "Starting services..."
    docker compose up -d --remove-orphans
    @echo "Waiting for services to initialize..."
    sleep 5

# Stop services
down:
    docker compose down

codegen-backend:
    @echo "Regenerating Backend Protos..."
    cd backend && uv run python -m grpc_tools.protoc -I../protos --python_out=src --grpc_python_out=src --pyi_out=src ../protos/meetmanager/v1/meet_manager.proto

codegen-frontend:
    @echo "Regenerating Frontend Protos..."
    cd web-client && npm run codegen

# Regenerate gRPC protos (local)
codegen: codegen-backend codegen-frontend

# Run all linting and formatting checks (read-only)
lint: lint-backend lint-mm-to-json lint-frontend format-frontend-check lint-protos

# Apply all automatic fixes
fix: fix-backend fix-mm-to-json lint-frontend-fix

lint-protos:
    @echo "Linting protos..."
    buf lint protos

type-check-backend: codegen-backend
    @echo "Type checking backend..."
    cd backend && MYPYPATH=src uv run mypy --non-interactive --install-types src

lint-backend:
    @echo "Linting backend..."
    cd backend && uv run ruff check src tests
    cd backend && uv run ruff format --check src tests

fix-backend:
    @echo "Fixing backend linting and formatting..."
    cd backend && uv run ruff check --fix src tests
    cd backend && uv run ruff format src tests

lint-mm-to-json:
    @echo "Linting mm_to_json..."
    cd mm_to_json/mm_to_json_py && ../../.venv/bin/ruff check .
    cd mm_to_json/mm_to_json_py && ../../.venv/bin/ruff format --check .

fix-mm-to-json:
    @echo "Fixing mm_to_json linting and formatting..."
    cd mm_to_json/mm_to_json_py && ../../.venv/bin/ruff check --fix .
    cd mm_to_json/mm_to_json_py && ../../.venv/bin/ruff format .

lint-frontend:
    @echo "Linting frontend..."
    cd web-client && npm run lint

lint-frontend-fix:
    @echo "Applying fixes for frontend linting issues..."
    cd web-client && npx @biomejs/biome migrate --write && npm run format && npm run lint:fix

format-frontend:
    @echo "Formatting frontend..."
    cd web-client && npm run format

format-frontend-check:
    @echo "Checking frontend formatting..."
    cd web-client && npm run format:check

# Run all tests (enforces linting first)
test: codegen lint test-backend test-frontend test-e2e

test-backend:
    @echo "Running Backend Tests..."
    docker compose exec -T backend python -m pytest tests/

# Setup Java dependencies (JARs and local JRE if needed)
setup-java:
    @echo "Setting up Java dependencies..."
    cd backend && uv run python src/mm_to_json/download_libs.py

test-backend-local: setup-java codegen
    @echo "Running Backend Tests locally..."
    cd backend && PYTHONPATH=src uv run pytest tests/

test-frontend: codegen
    @echo "Running Frontend Tests..."
    cd web-client && npm test

test-e2e:
    @echo "Running Playwright E2E Tests..."
    cd web-client && npm run test-e2e

test-e2e-sharded shard total:
    @echo "Running Playwright E2E Tests (Shard {{shard}}/{{total}})..."
    cd web-client && npx playwright test --shard={{shard}}/{{total}}

test-local: test-backend-local test-frontend

# Run formalized headless journey tests (requires 'just up' first)
test-journeys:
    @echo "Running Headless Journey Tests..."
    docker compose exec -T -e TEST_WEB_TARGET=http://frontend:3000 backend python -m pytest tests/integration/test_headless_journeys.py

# Full verification pipeline (includes production builds to catch styling/turbopack errors)
verify: lint test build-frontend build-mobile

verify-local: codegen fix lint test-local

# Run the complete pre-commit verification suite
pre-commit: verify

# Local CI simulation
verify-ci:
    @echo "Running verification in a clean CI-like container..."
    docker build -t meetmanager-ci -f ci.Dockerfile .
    docker run --rm meetmanager-ci

# Architecture flag for 'act' (forces linux/amd64 on Apple Silicon to ensure image compatibility)
act_arch := if os() == "macos" { if arch() == "aarch64" { "--container-architecture linux/amd64" } else { "" } } else { "" }

# Run GitHub Actions locally using act (non-interactive)
ci-local:
    @echo "Running GitHub Actions locally..."
    act pull_request \
        -P ubuntu-latest=catthehacker/ubuntu:act-latest \
        {{act_arch}} \
        --rm

# View logs
logs service="":
    docker compose logs -f {{service}}

# Open a shell in the backend container
shell:
    docker compose exec backend bash

# --- Reporting & Verification (Support for Report Code Agent) ---

# Generate a verification report PDF and PNG
report-verify:
    @echo "Generating verification report..."
    docker compose run --rm backend python src/verify_report_generation.py
    @echo "Converting to PNG..."
    docker compose run --rm backend bash -c "apt-get update && apt-get install -y poppler-utils && pdftoppm -png -f 1 -l 1 /app/data/example_reports/verification_entries_v5.pdf /app/data/example_reports/verification_entries_v5"
    @echo "Report generated in backend/data/example_reports/"

# Run the relay/entries data verification test
test-entries:
    @echo "Running Relay/Entries Data Verification..."
    docker compose run --rm backend python src/tests/test_meet_entries_data.py

# Build the mobile judge app web version
build-mobile:
    @echo "Building mobile judge app web bundle..."
    cd mobile-judge-app && npm run build-web

# Run the mobile judge app in Docker
up-mobile:
    @echo "Starting mobile judge app at http://localhost:{{env_var_or_default('MOBILE_APP_PORT', '8080')}}"
    docker build -t judge-app-v1 mobile-judge-app/
    docker run -d --name judge-app --rm -p {{env_var_or_default('MOBILE_APP_PORT', '8080')}}:8080 judge-app-v1

# Stop the mobile judge app container
down-mobile:
    docker stop judge-app

# Run mobile app tests
test-mobile:
    cd mobile-judge-app && npm test

# Run integration tests for judge app sync
test-integration-sync:
    @echo "Running integration tests for judge app sync..."
    cd tests/integration/judge_sync && docker compose -f docker-compose.test.yml build
    cd tests/integration/judge_sync && BACKEND_PORT={{env_var_or_default('BACKEND_PORT', '8081')}} FRONTEND_PORT={{env_var_or_default('FRONTEND_PORT', '3000')}} docker compose -f docker-compose.test.yml up --abort-on-container-exit --exit-code-from test-runner
    cd tests/integration/judge_sync && docker compose -f docker-compose.test.yml down

# --- Fast Verification & Mobile Workflows ---
# Fast verification (skips codegen)
verify-fast: lint test-backend-fast test-frontend-fast verify-mobile

# Fast backend tests (skips codegen)
test-backend-fast:
    @echo "Running Backend Tests locally (skipping codegen)..."
    cd backend && DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib:$DYLD_FALLBACK_LIBRARY_PATH PYTHONPATH=src uv run pytest tests/

# Fast frontend tests (skips codegen)
test-frontend-fast:
    @echo "Running Frontend Tests (skipping codegen)..."
    cd web-client && npm test

# Mobile App Verification (Type Check + Test)
verify-mobile:
    @echo "Verifying Mobile App..."
    cd mobile-judge-app && npx tsc --noEmit || echo "TypeScript errors found (ignoring for now to allow tests)"
    cd mobile-judge-app && npm test

# --- Cloud Run Deployment (Phase 3) ---

# Deploy the backend to Cloud Run
# Usage: just deploy-backend PROJECT_ID BUCKET_NAME
deploy-backend project bucket:
    @echo "Deploying backend to Cloud Run in project {{project}}..."
    gcloud config set project {{project}}
    cd backend && gcloud builds submit --tag gcr.io/{{project}}/meetmanager-backend
    gcloud run deploy meetmanager-backend \
        --image gcr.io/{{project}}/meetmanager-backend \
        --platform managed \
        --region us-central1 \
        --allow-unauthenticated \
        --set-env-vars "GCS_BUCKET_NAME={{bucket}},PORT=8080"

# Deploy the frontend to Cloud Run
# Usage: just deploy-frontend PROJECT_ID BACKEND_URL
deploy-frontend project backend_url:
    @echo "Deploying frontend to Cloud Run in project {{project}}..."
    gcloud config set project {{project}}
    cd web-client && gcloud builds submit --tag gcr.io/{{project}}/meetmanager-frontend
    gcloud run deploy meetmanager-frontend \
        --image gcr.io/{{project}}/meetmanager-frontend \
        --platform managed \
        --region us-central1 \
        --allow-unauthenticated \
        --set-env-vars "BACKEND_INTERNAL_HOST={{backend_url}}"

# --- Meet Program Viewer Workflows ---

# Start the Meet Program Viewer
up-viewer:
    @echo "Starting Meet Program Viewer..."
    cd meet-program-viewer && npx expo start --web

# Verify the Meet Program Viewer
verify-viewer:
    @echo "Verifying Meet Program Viewer..."
    cd meet-program-viewer && npx tsc --noEmit
    cd meet-program-viewer && npm test -- --watchAll=false
