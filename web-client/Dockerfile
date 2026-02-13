FROM node:20-alpine AS builder
RUN apk add --no-cache libc6-compat protobuf
WORKDIR /app

# 1. Install dependencies first (layer 1)
COPY web-client/package.json web-client/package-lock.json* ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

# 2. Copy protos and generate code (layer 2)
COPY protos/ /protos/
RUN mkdir -p lib/proto && \
  ./node_modules/.bin/grpc_tools_node_protoc \
  --plugin=protoc-gen-ts_proto=./node_modules/.bin/protoc-gen-ts_proto \
  --ts_proto_out=./lib/proto \
  --ts_proto_opt=outputServices=nice-grpc,outputServices=generic-definitions,useExactTypes=false,esModuleInterop=true \
  -I/protos \
  /protos/meetmanager/v1/meet_manager.proto

# 3. Copy web-client source and build (layer 3)
COPY web-client/ .
ENV NEXT_TELEMETRY_DISABLED 1
RUN npm run build

# Production image
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV production
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
ENV PORT 3000
CMD ["node", "server.js"]
