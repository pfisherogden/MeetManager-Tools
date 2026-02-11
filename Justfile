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

# Start services in the background
up:
    @echo "Starting services..."
    docker-compose up -d --remove-orphans
    @echo "Waiting for services to initialize..."
    sleep 5

# Stop services
down:
    docker-compose down

# Regenerate gRPC protos (local)
codegen:
    @echo "Regenerating Protos..."
    # Backend
    cd backend && uv run python -m grpc_tools.protoc -I../protos --python_out=src --grpc_python_out=src ../protos/meet_manager.proto
    # Frontend
    cd web-client && npm run codegen

# Run all linting and formatting checks
lint: lint-backend lint-mm-to-json

lint-backend:
    @echo "Linting backend..."
    cd backend && uv run ruff check .
    cd backend && uv run ruff format --check .

lint-mm-to-json:
    @echo "Linting mm_to_json..."
    cd mm_to_json/mm_to_json_py && ../../.venv/bin/ruff check .
    cd mm_to_json/mm_to_json_py && ../../.venv/bin/ruff format --check .

lint-frontend:
    @echo "Linting frontend (skipping as 'next lint' is unavailable in current version)..."
    # cd web-client && npm run lint

# Run all tests
test: test-backend test-frontend

test-backend:
    @echo "Running Backend Tests..."
    docker-compose exec -T backend python -m pytest tests/

test-frontend:
    @echo "Running Frontend Tests..."
    cd web-client && npm test

# Full verification pipeline
verify: lint test

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
