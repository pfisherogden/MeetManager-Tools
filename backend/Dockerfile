FROM python:3.11-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uv/bin/uv

# Install system dependencies
RUN apt-get update && apt-get install -y \
    mdbtools \
    openjdk-17-jre-headless \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies using uv
COPY backend/pyproject.toml .
# We don't have a lockfile yet, so we'll let uv create one or just install from pyproject
RUN /uv/bin/uv pip install --system -e .

# Copy protos and source
COPY protos ./protos
COPY backend/src ./src
COPY backend/tests ./tests
COPY backend/data ./data

# Download Java libraries
RUN python3 src/mm_to_json/download_libs.py

# Generate Python Protos
RUN python -m grpc_tools.protoc -Iprotos --python_out=src --grpc_python_out=src protos/meet_manager.proto

ENV PYTHONPATH=/app:/app/src
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 50051

CMD ["python", "src/server.py"]
