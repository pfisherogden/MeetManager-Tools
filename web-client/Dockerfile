FROM node:20-alpine

# Install system dependencies
RUN apk add --no-cache libc6-compat protobuf netcat-openbsd

WORKDIR /app

# Copy all files first
COPY . .

# Install root dependencies
RUN npm install

# Install web-client dependencies
WORKDIR /app/web-client
RUN npm install

# Build args
ARG NEXT_PUBLIC_E2E_AUTH_BYPASS
ENV NEXT_PUBLIC_E2E_AUTH_BYPASS=$NEXT_PUBLIC_E2E_AUTH_BYPASS

ARG NEXT_PUBLIC_AUTH_DISABLED
ENV NEXT_PUBLIC_AUTH_DISABLED=$NEXT_PUBLIC_AUTH_DISABLED

ARG NEXT_PUBLIC_BACKEND_PORT
ENV NEXT_PUBLIC_BACKEND_PORT=$NEXT_PUBLIC_BACKEND_PORT

# Build
RUN npm run build

EXPOSE 3000
ENV PORT=3000

# Start script with backend wait loop
# Next.js should find .next in the current directory (web-client)
CMD ["sh", "-c", "echo 'Waiting for backend:8080 (TCP)...' && until nc -z backend 8080; do sleep 2; done && echo 'Backend is UP, starting Next.js...' && npm start"]
