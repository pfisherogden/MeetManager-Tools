# MeetManager Tools

A suite of tools for processing and visualizing MeetManager `.mdb` data.

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

2.  **Run Verification**:
    ```bash
    just verify
    ```

3.  **Development**:
    - Backend: `just test-backend`
    - Frontend: `just test-frontend`

## Multi-User & Cloud Storage

The system now supports multi-user environments with strict data isolation.

- **Authentication**: Integrated with Firebase (Google Login). Every request from the web client is verified using ID tokens.
- **Data Isolation**: Each user has a private sandbox. Datasets and configurations are stored under `users/[UID]/` paths.
- **Storage Providers**: Supports local file system (default) and Google Cloud Storage (GCS) for production.

For detailed setup instructions (including GCS configuration), see the [Backend README](./backend/README.md#cloud-storage--multi-user-setup).

## CI/CD

This repository uses GitHub Actions for Continuous Integration.

- **Backend**: Runs `ruff` (lint/format) and `pytest`.
- **Frontend**: Runs `biome` (lint/format) and `vitest`.
- **Path Filtering**: Workflows run only when relevant files are changed.
\n
