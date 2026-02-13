---
name: Architecture Guidelines
description: Project structure and decoupling principles for MeetManager-Tools. Use when refactoring, adding new services, or modifying system-wide communication.
---

# Architecture Guidelines

## Structural Principles
- **Service Isolation**: Maintain `backend` (Python) and `web-client` (Next.js) as decoupled services.
- **Contract-First**: Use gRPC Protobuf definitions in `protos/` as the single source of truth for cross-service communication.
- **Hermetic Builds**: Ensure all build processes are self-contained within Docker.
- **Docker Optimization**: 
    - **Layered Dependencies**: Copy dependency files (`package.json`, `pyproject.toml`, `uv.lock`) and run install/sync steps *before* copying full source code.
    - **Isolation**: Isolate slow, static steps (e.g., JRE downloads) in early layers to maximize build cache reuse.

## Data Strategy
- **Source of Truth**: Treat Microsoft Access (`.mdb`) files as the primary data source.
- **Caching**: Utilize JSON caching for performance, but ensure it is reproducible from the MDB source.
- **Verification**: Ensure every data transformation is verifiable via automated PDF/PNG reports.

## Frontend Architecture
- **Server-First**: Prioritize React Server Components and Server Actions.
- **State**: Minimize client-side state; leverage URL parameters and server-side data fetching.
- **Consistency**: Use `revalidatePath` to synchronize UI state after server-side mutations.

## Verification Workflow
- **Local Check**: Run `just verify-local` before pushing to verify codegen, linting, and tests.
- **Hermetic Check**: Run `just verify-ci` for a clean-room Docker verification in `ci.Dockerfile`.