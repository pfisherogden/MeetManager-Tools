# Build stage
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

# Copy the rest of the application
COPY web-client/ .

ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_OPTIONS="--max-old-space-size=4096"

ARG NEXT_PUBLIC_E2E_AUTH_BYPASS
ENV NEXT_PUBLIC_E2E_AUTH_BYPASS=$NEXT_PUBLIC_E2E_AUTH_BYPASS

# Build the Next.js application
RUN npm run build

# Production image
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production

# Install netcat for health checks
RUN apk add --no-cache netcat-openbsd

# Copy the entire build (non-standalone for simplicity)
COPY --from=builder /app ./

EXPOSE 3000
ENV PORT=3000

# Start script with backend wait loop and production server
CMD ["sh", "-c", "echo 'Waiting for backend:8080 (TCP)...' && until nc -z backend 8080; do sleep 2; done && echo 'Backend is UP, starting Next.js...' && npm start"]
