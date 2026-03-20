# MMTools
A suite of tools for processing and visualizing swim meet data.


## Table of Contents

- [Backend](./backend): Python-based server and API for processing meet data.
- [Web Client](./web-client): Next.js/React frontend for interacting with the data.
- [Mobile Judge App](./mobile-judge-app): Offline-first Expo app for swim meet officiating. ([Demo](https://pfisherogden.github.io/MeetManager-Tools/))
- [mm_to_json](./mm_to_json): Core library for converting `.mdb` files to JSON.

## Getting Started

### Prerequisites

- [Docker](https://www.docker.com/) & Docker Compose
- [Just](https://github.com/casey/just) (Command runner)
- [uv](https://github.com/astral-sh/uv) (Python package manager)
- [Node.js](https://nodejs.org/) (v20+)

### System Dependencies (macOS)
The backend requires system libraries for PDF generation (WeasyPrint).
```bash
brew install glib pango cairo gdk-pixbuf libffi
```


### Quick Start

1.  **Start Services**:
    ```bash
    just up
    ```

2.  **Run Full Verification (Mandatory before push)**:
    ```bash
    just pre-commit
    ```
    This command runs linters, tests, and validates that both frontend and mobile apps compile correctly.

3.  **Development**:
    - Backend: `just test-backend`
    - Frontend: `just test-frontend`

## Multi-User & Cloud Storage

The system now supports multi-user environments with strict data isolation.

- **Authentication**: Integrated with Firebase (Google Login). Every request from the web client is verified using ID tokens.
- **Data Isolation**: Each user has a private sandbox. Datasets and configurations are stored under `users/[UID]/` paths.
- **Storage Providers**: Supports local file system (default) and Google Cloud Storage (GCS) for production.

For detailed setup instructions (including GCS configuration), see the [Backend README](./backend/README.md#cloud-storage--multi-user-setup).

### Security & Access Control

To protect meet data and prevent unauthorized DQ submissions, the system uses a `DATA_ACCESS_TOKEN`.

#### Generating a Secret Token
You can generate a secure random string using `openssl`:
```bash
openssl rand -base64 32
```

#### Configuration
1.  **Local/Docker**: Set `DATA_ACCESS_TOKEN` in your `.env` file.
2.  **GitHub Actions**: Add `DATA_ACCESS_TOKEN` as a repository secret.
3.  **Google Cloud (Cloud Run)**: 
    - Store the token in **Secret Manager**.
    - Expose it as an environment variable `DATA_ACCESS_TOKEN` to both the `backend` and `frontend` services.

## CI/CD

This repository uses GitHub Actions for Continuous Integration.

- **Unified Verification**: Locally, always run `just pre-commit` to catch build-time errors before they reach CI.
- **Backend**: Runs `ruff` (lint/format) and `pytest`.
- **Frontend**: Runs `biome` (lint/format), `vitest`, and production builds (`next build`, `expo export`).
- **End-to-End**: Runs browser-based journeys using Playwright (`just test-e2e`).
- **Path Filtering**: Workflows run only when relevant files are changed.
\n
