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

# Copy source code (respecting .dockerignore)
COPY . .

# Install dependencies (this makes the image large but the run fast)
RUN uv sync --all-packages --dev
RUN cd web-client && npm install

# The rest will be handled by running 'just verify'
CMD ["just", "verify"]
