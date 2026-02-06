FROM node:20-alpine AS builder
RUN apk add --no-cache libc6-compat protobuf
WORKDIR /app

# Install dependencies (single stage to avoid COPY --from hang)

# Install dependencies (single stage to avoid COPY --from hang)
# Install dependencies
COPY package.json package-lock.json* ./
RUN if [ -f package-lock.json ]; then npm ci; else echo "Lockfile not found. Running npm install." && npm install; fi

# Copy source
COPY . .
# Protos are now in backend_protos_temp (copied by Justfile)

# Generate TS Code
RUN mkdir -p lib/proto && \
  ./node_modules/.bin/grpc_tools_node_protoc \
  --plugin=protoc-gen-ts_proto=./node_modules/.bin/protoc-gen-ts_proto \
  --ts_proto_out=./lib/proto \
  --ts_proto_opt=outputServices=nice-grpc,outputServices=generic-definitions,useExactTypes=false,esModuleInterop=true \
  -I./backend_protos_temp \
  ./backend_protos_temp/meet_manager.proto

# Build
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
