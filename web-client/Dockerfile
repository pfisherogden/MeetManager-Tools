FROM node:20-alpine

# Install system dependencies
RUN apk add --no-cache libc6-compat protobuf netcat-openbsd

WORKDIR /app

# Copy root package.json for just/scripts
COPY package.json package-lock.json* ./
RUN npm install

# Copy protos (needed for codegen)
# Root context is project root, so protos is at ./protos
COPY protos/ /app/protos/

# Setup web-client
WORKDIR /app/web-client
COPY web-client/package.json web-client/package-lock.json* ./
RUN npm install

# Copy web-client source BEFORE build so codegen can run
COPY web-client/ .

# Build args
ARG NEXT_PUBLIC_E2E_AUTH_BYPASS
ENV NEXT_PUBLIC_E2E_AUTH_BYPASS=$NEXT_PUBLIC_E2E_AUTH_BYPASS

ARG NEXT_PUBLIC_AUTH_DISABLED
ENV NEXT_PUBLIC_AUTH_DISABLED=$NEXT_PUBLIC_AUTH_DISABLED

ARG NEXT_PUBLIC_BACKEND_PORT
ENV NEXT_PUBLIC_BACKEND_PORT=$NEXT_PUBLIC_BACKEND_PORT

# Build (this triggers codegen which needs ../protos)
RUN npm run build

EXPOSE 3000
ENV PORT=3000

# Start script with backend wait loop
CMD ["sh", "-c", "echo 'Waiting for backend:8080 (TCP)...' && until nc -z backend 8080; do sleep 2; done && echo 'Backend is UP, starting Next.js...' && npm start"]
