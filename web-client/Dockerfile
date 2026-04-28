# Build stage
FROM node:20-alpine AS builder

ARG NEXT_PUBLIC_E2E_AUTH_BYPASS
ENV NEXT_PUBLIC_E2E_AUTH_BYPASS=$NEXT_PUBLIC_E2E_AUTH_BYPASS

ARG NEXT_PUBLIC_AUTH_DISABLED
ENV NEXT_PUBLIC_AUTH_DISABLED=$NEXT_PUBLIC_AUTH_DISABLED

# Install system dependencies
RUN apk add --no-cache libc6-compat protobuf

WORKDIR /app

# Install dependencies
COPY web-client/package.json web-client/package-lock.json* ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

# Copy protos and generate client
COPY protos/ /protos/
# Copy the rest of the application
COPY web-client/ .

ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_OPTIONS="--max-old-space-size=4096"

ARG NEXT_PUBLIC_E2E_AUTH_BYPASS
ENV NEXT_PUBLIC_E2E_AUTH_BYPASS=$NEXT_PUBLIC_E2E_AUTH_BYPASS

ARG NEXT_PUBLIC_AUTH_DISABLED
ENV NEXT_PUBLIC_AUTH_DISABLED=$NEXT_PUBLIC_AUTH_DISABLED

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
