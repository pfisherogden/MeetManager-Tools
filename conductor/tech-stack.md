# Tech Stack: MeetManager-Tools

## Current Stack (Local/Docker)

### Frontend: Web Client
- **Framework**: Next.js 15 (App Router, TypeScript)
- **Styling**: Tailwind CSS + Shadcn UI
- **Communication**: gRPC-web via `nice-grpc` and `grpc-web` proxy.
- **Location**: `./web-client`

### Frontend: Mobile Judge App
- **Framework**: React Native (Expo SDK, Managed Workflow)
- **Database**: SQLite (via `expo-sqlite`) for offline persistence.
- **Location**: `./mobile-judge-app`

### Backend: Python (Server)
- **Runtime**: Python 3.9+
- **Framework**: gRPC (AsyncIO)
- **MDB Parsing**: In-process Jackcess library (via JPype) or `mdbtools` fallback.
- **Reporting**: WeasyPrint + Jinja2.
- **Location**: `./backend`

### Shared Infrastructure
- **API Definition**: Protobuf (Stored in `/protos`).
- **Build/Automation**: `just` (Justfile), Docker, Docker Compose.

## Planned Cloud Migration

### 1. Identity & Auth (Firebase)
- **Provider**: Firebase Authentication.
- **Methods**: Google OAuth2.
- **Backend Verification**: `firebase-admin` SDK for JWT verification.

### 2. Multi-User Storage (GCS)
- **Provider**: Google Cloud Storage (GCS).
- **Isolation**: Per-user directory structure (`users/[UID]/...`).
- **Abstraction**: Abstract `StorageProvider` in the Python backend.

### 3. Deployment (GCP)
- **Backend**: Google Cloud Run (Containerized gRPC).
- **Frontend**: Google Cloud Run (Next.js server).
- **CI/CD**: GitHub Actions deploying to Artifact Registry and Cloud Run.
- **Infrastructure**: Terraform for resource provisioning.
