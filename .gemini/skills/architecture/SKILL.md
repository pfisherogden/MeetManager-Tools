---
name: Architecture Guidelines
description: Project structure and decoupling principles.
---
# Architecture Guidelines

## Project Structure
- **Service Isolation**: The repository consists of `backend` (Python) and `web-client` (Next.js) as independent services.
- **Contract-First**: gRPC Protobuf definitions are the single source of truth for communication. They reside in the root `protos/` directory.
- \*\*Hermetic Builds\*\*: Build processes must be self-contained within Docker. Avoid host-side scripts that modify the project structure during builds.

## Data & Reporting
- **Persistence**: Database state is managed via Microsoft Access (`.mdb`) files, with JSON caching for performance.
- **Verification**: Every data transformation must be verifiable through automated reports (PDF/PNG artifacts) to ensure correctness against the original MDB source.

## Frontend Strategy
- **Data Fetching**: Prefer Server Components and Server Actions.
- **State Management**: Minimize client-side state; use URL params or server-side data where possible.
- **Caching**: Use `revalidatePath` to maintain consistency after admin actions.

## DevOps & Infrastructure
- **Environment Parity**: Maintain strict tool parity between local development, Docker environments, and CI/CD pipelines.
- **Local CI Verification**: Before pushing changes, run `just verify-ci`. This executes the full pipeline in a clean room Docker container (`ci.Dockerfile`) to catch missing dependencies or configuration errors that only appear in hermetic environments.