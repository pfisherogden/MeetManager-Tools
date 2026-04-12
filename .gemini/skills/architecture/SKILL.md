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
- **Bundled Feature Parity**: When adding new visual flags or filters (e.g., Zebra Striping) to individual reports, ensure they are also exposed in the **Custom Report Pack Builder**. This prevents architectural drift where bundled reports lack the capabilities of individual ones.

## Mobile App (Expo)
- **Offline-First**: Use `expo-sqlite` for local persistence. Implement a cross-platform database shim (`db.ts`) to handle web vs native environments.
- **Sub-path Hosting**: For GitHub Pages deployment, `experiments.baseUrl` in `app.config.js` MUST match the repository name combined with the app path (e.g., `"/MeetManager-Tools/judge"`).
- **SPA Coexistence**: To host multiple Expo SPAs on a single GitHub Pages domain, build them to separate subdirectories (e.g., `/judge` and `/viewer`) and use a custom `public/index.html` at the root for navigation. 
- **Dynamic Build Injection**: Use a `prebuild-web` npm script with a custom Node.js file to dynamically replace constant values (like timestamps or versions) in source files just before the Expo bundler executes.
- **Static Assets**: Avoid `output: "static"` if not using Expo Router, as it introduces unnecessary dependencies. Use standard SPA bundling.
- **Web Compatibility**: Ensure files starting with underscores (like `_expo/`) are served by adding a `.nojekyll` file to the build root.
- **Protobuf Case Sensitivity**: When communicating between Python (backend) and TypeScript (frontend/mobile) via gRPC, be mindful of property casing. Protobuf compilers generate **snake_case** for Python and **camelCase** for TypeScript. Mismatches will result in `AttributeError` or missing data.
- **Property Resilience**: In decoupled environments (where mobile apps might lag behind backend updates), use **property fallbacks** when reading data (e.g., `const name = item.members || item.relaySwimmers || []`). This ensures continuity when internal JSON keys are renamed or migrated.

## Cloud Native & Serverless (Cloud Run)
- **Memory Management**: For resource-intensive tasks (e.g., WeasyPrint PDF generation), assume a **2GB-4GB limit**. Limit parallelism (e.g., `max_workers = 1`) to prevent OOM errors in serverless environments.
- **gRPC Message Limits**: Default 4MB limits are insufficient for binary data (ZIPs/PDFs). Explicitly configure **50MB limits** on both server and client channels.
- **Serialization Boundaries**: Avoid passing raw binary (`Uint8Array`, `bytes`) through Next.js Server Action boundaries in production standalone builds. Utilize **Base64 strings** for reliable serialization and transport between server and client components.
- **GCS Proxy Pattern**: For large binary payloads (ZIP bundles), use a **Proxy Strategy**: Upload the file to GCS and return a proxy URL (`/api/data?path=...`) instead of transmitting the raw binary over gRPC. This improves memory stability and prevents timeouts.
- **Stateless Authentication**: Use a shared secret (`DATA_ACCESS_TOKEN`) for authorized system-level access between decoupled services (e.g., Next.js frontend proxying for a mobile app).

## Verification Workflow
- **Local Check**: Run `just verify-local` before pushing to verify codegen, linting, and tests.
- **Hermetic Check**: Run `just verify-ci` for a clean-room Docker verification in `ci.Dockerfile`.