set shell := ["bash", "-c"]

# Default recipe
default: test

# Ensure Colima is started
colima-start:
    @if ! colima status >/dev/null 2>&1; then \
        echo "Colima is not running. Starting Colima..."; \
        colima start; \
    fi

# Clean up temporary cache files
clean:
    @echo "Cleaning up..."
    -rm -rf .tmp
    -rm -rf .npm_cache
    -rm -rf backend/src/__pycache__
    -rm -f backend/data/uploaded.mdb
    @echo "Cleanup complete."

# Download required Java libraries
setup:
    @echo "Downloading Java libraries..."
    python3 backend/src/mm_to_json/download_libs.py

# Build Docker containers
build: colima-start clean setup
    @echo "Preparing frontend build context..."
    mkdir -p web-client/backend_protos_temp
    cp -r backend/protos/* web-client/backend_protos_temp/
    @echo "Building containers..."
    docker-compose build
    @echo "Cleaning up temp protos..."
    rm -rf web-client/backend_protos_temp

# Start services in the background
up: colima-start
    @echo "Starting services..."
    docker-compose up -d --remove-orphans
    @echo "Waiting for services to initialize..."
    sleep 5

# Regenerate gRPC protos inside the container
codegen:
    @echo "Regenerating Protos inside container..."
    docker-compose run --rm backend python -m grpc_tools.protoc -Iprotos --python_out=src --grpc_python_out=src protos/meet_manager.proto

# Run backend tests
test: build codegen up
    @echo "Running Backend Tests..."
    docker-compose exec -T backend python -m pytest tests/

# Stop services
down:
    docker-compose down

# View logs
logs service="":
    docker-compose logs -f {{service}}

# Generate a verification report PDF and PNG (V5)
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

# Run full backend tests
test-full:
    @echo "Running Full Backend Tests..."
    docker-compose run --rm backend pytest tests/

# Open a shell in the backend container
shell:
    docker-compose exec backend bash
