FROM node:20-alpine AS judge-builder
WORKDIR /app/mobile-judge-app
COPY mobile-judge-app/package.json mobile-judge-app/package-lock.json* ./
RUN npm ci
COPY mobile-judge-app/ .
# Expo export web
RUN APP_BASE_URL=/judge npm run build-web

FROM node:20-alpine
RUN apk add --no-cache libc6-compat protobuf netcat-openbsd
WORKDIR /app

# Copy protos
COPY protos/ /app/protos/

# Copy root for scripts
COPY package.json package-lock.json* ./
RUN npm install

# Build web-client
WORKDIR /app/web-client
COPY web-client/package.json web-client/package-lock.json* ./
RUN npm ci

# Copy judge app dist from builder
RUN mkdir -p /app/web-client/public/judge
COPY --from=judge-builder /app/mobile-judge-app/dist /app/web-client/public/judge

# Copy web-client source
COPY web-client/ .

# Build
ARG NEXT_PUBLIC_E2E_AUTH_BYPASS
ENV NEXT_PUBLIC_E2E_AUTH_BYPASS=$NEXT_PUBLIC_E2E_AUTH_BYPASS
ARG NEXT_PUBLIC_AUTH_DISABLED
ENV NEXT_PUBLIC_AUTH_DISABLED=$NEXT_PUBLIC_AUTH_DISABLED
ARG NEXT_PUBLIC_BACKEND_PORT
ENV NEXT_PUBLIC_BACKEND_PORT=$NEXT_PUBLIC_BACKEND_PORT

RUN npm run codegen && npm run build

EXPOSE 3000
ENV PORT=3000
CMD ["sh", "-c", "if [ \"$WAIT_FOR_BACKEND\" = \"true\" ]; then echo 'Waiting for backend:8080...'; until nc -z backend 8080; do sleep 2; done; fi && npm start"]
