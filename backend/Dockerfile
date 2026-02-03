FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    mdbtools \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
RUN pip install grpcio grpcio-tools pytest

# Copy only the backend directory content
COPY . .

# Generate Python Protos (Fix for UNIMPLEMENTED error)
RUN python -m grpc_tools.protoc -Iprotos --python_out=src --grpc_python_out=src protos/meet_manager.proto

# Add src and protos to path
ENV PYTHONPATH=/app:/app/src:/app/src/protos
ENV PYTHONPATH=/app:/app/src:/app/src/protos
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 50051

# Run server (path relative to WORKDIR /app, which now contains src/)
CMD ["python", "src/server.py"]
