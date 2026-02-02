# MeetManager Tools

Tools to parse and display detailed swim meet data from Meet Manager `.mdb` files.

[Architecture Documentation](docs/ARCHITECTURE.md)

## Project Structure

- **`backend/`**: Python gRPC server. Handles MDB parsing and data service.
- **`web-client/`**: Next.js Frontend. Provides the Dashboard, Browser, and Admin UI.
- **`mm_to_json/`**: Original/Legacy tools for direct MDB-to-JSON conversion.

## Quick Start (Docker)

This project requires Docker and Docker Compose.

```bash
# Start the full stack
docker-compose up -d --build
```
Access the application at `http://localhost:3000`.

## Features
- **Admin Dashboard**: Upload `.mdb` files directly from the UI (`/admin`).
- **Data Visualization**: View Meets, Teams, Athletes, and Entries.
- **Relays & Scores**: View computed scores and relay teams.

## Development

Each sub-project can be developed independently. See `backend/README.md` and `web-client/README.md` for details.
