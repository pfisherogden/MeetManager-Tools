# Build stage (Only for dependencies)
FROM node:20-alpine AS builder

# Install system dependencies
RUN apk add --no-cache libc6-compat protobuf

WORKDIR /app

# Install dependencies
COPY web-client/package.json web-client/package-lock.json* ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

# Copy protos and generate client
COPY protos/ /protos/
RUN mkdir -p lib/proto && \
  ./node_modules/.bin/grpc_tools_node_protoc \
  --plugin=protoc-gen-ts_proto=./node_modules/.bin/protoc-gen-ts_proto \
  --ts_proto_out=./lib/proto \
  --ts_proto_opt=outputServices=nice-grpc,outputServices=generic-definitions,useExactTypes=false,esModuleInterop=true \
  -I/protos \
  /protos/meetmanager/v1/meet_manager.proto

# E2E/Development image (using Dev server with volume mounts)
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=development

# Install netcat for health checks
RUN apk add --no-cache netcat-openbsd

# Copy dependencies and proto libs from builder
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/lib ./lib

# The rest of the app will be mounted via volume in docker-compose

EXPOSE 3000
ENV PORT=3000

# Start script with backend wait loop and dev server
CMD ["sh", "-c", "echo 'Waiting for backend:8080 (TCP)...' && until nc -z backend 8080; do sleep 2; done && echo 'Backend is UP, starting Next.js Dev Server...' && npm run dev"]
