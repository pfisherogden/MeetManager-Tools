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

### Installation
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Running Locally
```bash
python src/server.py
```

### Docker
```bash
docker-compose up backend
```

## API Definition
See `protos/meet_manager.proto` for the full Service definition.
