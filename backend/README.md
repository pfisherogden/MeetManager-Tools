# MeetManager gRPC Backend

A Python gRPC service for parsing and serving Swim Meet data from `.mdb` (Microsoft Access) or `.json` files.

## Features
- **MDB Parsing**: Uses `mdb-export` (via `mdbtools`) to read legacy Meet Manager databases.
- **gRPC API**: Exposes Meets, Teams, Athletes, Entries, and Scores via a strongly-typed gRPC interface.
- **Admin API**: Supports uploading and selecting active datasets.

## Development

### Prerequisites
- Python 3.11+
- `mdbtools` (for MDB parsing)
- `uv` (for dependency management)

### Installation
```bash
cd backend
uv sync --all-extras --dev
```

### Running Locally
```bash
uv run python src/server.py
```

### Running Tests (Locally)
To run tests outside of Docker, you must regenerate the protobuf code locally and ensure dependencies are installed:

```bash
# 1. Install dependencies
uv sync --all-extras --dev

# 2. Generate Protos (using just)
just codegen

# 3. Run Tests (using just)
just test-backend
```

### Docker
```bash
docker-compose up backend
```

## API Definition
See `protos/meetmanager/v1/meet_manager.proto` for the full Service definition.
