set shell := ["bash", "-c"]

# Default recipe
default: test

# Clean up temporary cache files
clean:
    @echo "Cleaning up..."
    -rm -rf .tmp
    -rm -rf .npm_cache
    -rm -rf backend/src/__pycache__
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
