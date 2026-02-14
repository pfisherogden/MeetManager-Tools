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

## Python Circular Import Prevention
- **Avoid Coupling**: Avoid importing complex classes (like `MmToJsonConverter`) at the top level of reporting or utility modules.
- **Use TYPE_CHECKING**: Utilize `from typing import TYPE_CHECKING` guards for type hints only.
- **Lazy Imports**: Import heavy generator or renderer classes inside the specific functions where they are used (e.g., inside `main()` or a specific RPC implementation) to prevent partially initialized module errors.

## Frontend Architecture
- **Server-First**: Prioritize React Server Components and Server Actions.
- **State**: Minimize client-side state; leverage URL parameters and server-side data fetching.
- **Consistency**: Use `revalidatePath` to synchronize UI state after server-side mutations.

## Verification Workflow
- **Local Check**: Run `just verify-local` before pushing to verify codegen, linting, and tests.
- **Hermetic Check**: Run `just verify-ci` for a clean-room Docker verification in `ci.Dockerfile`.