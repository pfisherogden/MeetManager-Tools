FROM python:3.11-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uv/bin/uv
ENV PATH="/uv/bin:${PATH}"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    mdbtools \
    openjdk-21-jre-headless \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install just
RUN curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | bash -s -- --to /usr/local/bin

WORKDIR /app

# 1. Install Python dependencies first (layer 1)
COPY pyproject.toml uv.lock ./
COPY backend/pyproject.toml backend/uv.lock ./backend/
COPY mm_to_json/mm_to_json_py/pyproject.toml mm_to_json/mm_to_json_py/uv.lock ./mm_to_json/mm_to_json_py/
RUN uv sync --all-packages --dev

# 2. Install Node dependencies (layer 2)
COPY web-client/package.json web-client/package-lock.json* ./web-client/
RUN cd web-client && npm install

# 3. Copy the rest of the source code (layer 3)
COPY . .

# The rest will be handled by running 'just verify-local'
CMD ["just", "verify-local"]
