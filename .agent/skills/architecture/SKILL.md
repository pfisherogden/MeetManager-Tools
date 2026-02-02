---
name: Architecture Guidelines
description: Project structure and decoupling principles.
---
# Architecture Guidelines

## Project Independence
- **Structure**: This repository contains two distinct projects:
  1. `backend` (Python/gRPC)
  2. `web-client` (Next.js)
- **Principle**: Treat them as loosely coupled services. They may be split into separate repositories in the future.
- **Restriction**: Avoid tight coupling or shared code outside of defined API contracts (gRPC protos).

## Frontend Strategy
- **Data Fetching**: Prefer Server Components.
- **Caching**: Be mindful of Next.js caching. Use `force-dynamic` or `revalidatePath` for admin/data-heavy views to ensure data consistency.
