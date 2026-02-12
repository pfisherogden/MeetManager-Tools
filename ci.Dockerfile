FROM python:3.11-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uv/bin/uv
ENV PATH="/uv/bin:${PATH}"

# Install system dependencies
RUN apt-get update && apt-get install -y 
    curl 
    mdbtools 
    openjdk-17-jre-headless 
    && rm -rf /var/lib/apt/lists/*

# Install just
RUN curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | bash -s -- --to /usr/local/bin

WORKDIR /app

# The rest will be handled by mounting the volume and running 'just verify'
CMD ["just", "verify"]
