# MeetManager Tools

A suite of tools for processing and visualizing MeetManager `.mdb` data.

## Table of Contents

- [Backend](./backend): Python-based server and API for processing meet data.
- [Web Client](./web-client): Next.js/React frontend for interacting with the data.
- [mm_to_json](./mm_to_json): Core library for converting `.mdb` files to JSON.

## Getting Started

### Prerequisites

- [Docker](https://www.docker.com/) & Docker Compose
- [Just](https://github.com/casey/just) (Command runner)
- [uv](https://github.com/astral-sh/uv) (Python package manager)
- [Node.js](https://nodejs.org/) (v20+)

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

## CI/CD

This repository uses GitHub Actions for Continuous Integration.

- **Backend**: Runs `ruff` (lint/format) and `pytest`.
- **Frontend**: Runs `biome` (lint/format) and `vitest`.
- **Path Filtering**: Workflows run only when relevant files are changed.
