set shell := ["bash", "-c"]

# Default recipe
default: verify

# Clean up temporary cache files
clean:
    @echo "Cleaning up..."
    -rm -rf .tmp
    -rm -rf .npm_cache
    -rm -rf backend/src/__pycache__
    -rm -rf web-client/.next
    -rm -f backend/data/uploaded.mdb
    @echo "Cleanup complete."

# Build Docker containers
build: clean
    @echo "Building containers..."
    docker-compose build

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
    docker-compose up -d --remove-orphans
    @echo "Waiting for services to initialize..."
    sleep 5

# Stop services
down:
    docker-compose down

codegen-backend:
    @echo "Regenerating Backend Protos..."
    cd backend && uv run python -m grpc_tools.protoc -I../protos --python_out=src --grpc_python_out=src --pyi_out=src ../protos/meetmanager/v1/meet_manager.proto

codegen-frontend:
    @echo "Regenerating Frontend Protos..."
    cd web-client && npm run codegen

# Regenerate gRPC protos (local)
codegen: codegen-backend codegen-frontend

# Run all linting and formatting checks (read-only)
lint: lint-backend lint-mm-to-json lint-frontend format-frontend-check lint-protos type-check-backend

# Apply all automatic fixes
fix: fix-backend fix-mm-to-json lint-frontend-fix

lint-protos:
    @echo "Linting protos..."
    buf lint protos

type-check-backend: codegen-backend
    @echo "Type checking backend..."
    cd backend && MYPYPATH=src uv run mypy src

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
test: codegen lint test-backend test-frontend

test-backend:
    @echo "Running Backend Tests..."
    docker-compose exec -T backend python -m pytest tests/

# Setup Java dependencies (JARs and local JRE if needed)
setup-java:
    @echo "Setting up Java dependencies..."
    cd backend && uv run python src/mm_to_json/download_libs.py

test-backend-local: setup-java codegen
    @echo "Running Backend Tests locally..."
    cd backend && uv run pytest tests/

test-frontend: codegen
    @echo "Running Frontend Tests..."
    cd web-client && npm test

test-local: test-backend-local test-frontend

# Full verification pipeline
verify: lint test

verify-local: codegen fix lint test-local

# Local CI simulation
verify-ci:
    @echo "Running verification in a clean CI-like container..."
    docker build -t meetmanager-ci -f ci.Dockerfile .
    docker run --rm meetmanager-ci

# View logs
logs service="":
    docker-compose logs -f {{service}}

# Open a shell in the backend container
shell:
    docker-compose exec backend bash

# --- Reporting & Verification (Support for Report Code Agent) ---

# Generate a verification report PDF and PNG
report-verify:
    @echo "Generating verification report..."
    docker-compose run --rm backend python src/verify_report_generation.py
    @echo "Converting to PNG..."
    docker-compose run --rm backend bash -c "apt-get update && apt-get install -y poppler-utils && pdftoppm -png -f 1 -l 1 /app/data/example_reports/verification_entries_v5.pdf /app/data/example_reports/verification_entries_v5"
    @echo "Report generated in backend/data/example_reports/"

# Run the relay/entries data verification test
test-entries:
    @echo "Running Relay/Entries Data Verification..."
    docker-compose run --rm backend python src/tests/test_meet_entries_data.py
