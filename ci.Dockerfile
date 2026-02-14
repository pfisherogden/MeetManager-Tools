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
    libpango-1.0-0 \
    libharfbuzz0b \
    libpangoft2-1.0-0 \
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

# Install buf
RUN BIN="/usr/local/bin" && \
    VERSION="1.30.0" && \
    curl -sSL \
    "https://github.com/bufbuild/buf/releases/download/v${VERSION}/buf-$(uname -s)-$(uname -m)" \
    -o "${BIN}/buf" && \
    chmod +x "${BIN}/buf"

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
