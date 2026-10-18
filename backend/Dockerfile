FROM rust:1-slim-bookworm AS rust-builder
WORKDIR /build/rust
COPY backend/rust ./
WORKDIR /build/rust/mm_core_rs
RUN cargo build --release

FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uv/bin/uv

# Install system dependencies
RUN apt-get update && apt-get install -y \
    mdbtools \
    openjdk-21-jre-headless \
    libpango-1.0-0 \
    libharfbuzz0b \
    libpangoft2-1.0-0 \
    libglib2.0-0 \
    libffi-dev \
    libjpeg-dev \
    libopenjp2-7-dev \
    libgbm1 \
    libasound2 \
    libnss3 \
    libnspr4 \
    libxss1 \
    libxtst6 \
    libxshmfence1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 1. Install Python dependencies using uv (layer 1)
COPY backend/pyproject.toml backend/uv.lock* ./
RUN /uv/bin/uv pip install --system --no-cache .
RUN python -m playwright install --with-deps chromium && rm -rf /var/lib/apt/lists/* /root/.cache

# 2. Download Java libraries (layer 2 - depends only on script and config)
COPY backend/src/mm_to_json/download_libs.py ./src/mm_to_json/
RUN python3 src/mm_to_json/download_libs.py

# 3. Generate Python Protos (layer 3 - depends only on protos)
COPY protos ./protos
RUN python -m grpc_tools.protoc -Iprotos --python_out=src --grpc_python_out=src --pyi_out=src protos/meetmanager/v1/meet_manager.proto

# 4. Copy source, data, and compiled Rust engine (layer 4)
COPY backend/src ./src
COPY backend/data ./data
COPY --from=rust-builder /build/rust/mm_core_rs/target/release/libmm_core_rs.so ./src/mm_to_json/lib/libmm_core_rs.so

ENV PYTHONPATH=/app:/app/src
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV MM_ENGINE=rust
ENV PORT=8080

EXPOSE 8080

CMD ["python", "src/server.py"]
