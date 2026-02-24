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

## CI/Test Strategy

- **JSON Fixtures**: For CI stability and fresh checkouts, all core reporting tests use committed JSON fixtures located in `tests/fixtures/anonymized_meets/`. This removes the dependency on `.mdb` files which are gitignored.
- **Mypy**: CI enforces strict type checking. Ensure all new logic in `extractor.py` and service layers has explicit type signatures.

## Reliability Standards

- **5-Cycle Verification**: For all major implementations or bug fixes, run the test suite (`just test-backend`) **5 times consecutively**. All 5 runs must pass 100% to ensure no intermittent flakiness or race conditions exist.

## Cloud Storage & Multi-User Setup

This backend supports multi-user data isolation and cloud storage using Google Cloud Storage (GCS).

### 1. Configure Google Cloud Storage
1.  **Create a Bucket**: Create a private GCS bucket (e.g., `meetmanager-data-prod`).
2.  **Enable GCS API**: Ensure the Google Cloud Storage API is enabled in your project.
3.  **Service Account**: Create a Service Account with `Storage Object Admin` permissions for the bucket.
4.  **Credentials**: Download the JSON key for the service account.

### 2. Environment Variables
Set the following environment variables in your environment (Local or Cloud Run):

| Variable | Description | Example |
| :--- | :--- | :--- |
| `GCS_BUCKET_NAME` | The name of your GCS bucket. | `meetmanager-data-prod` |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to your Service Account JSON key. | `/path/to/key.json` |
| `GRPC_AUTH_DISABLED` | Set to `true` to skip Firebase validation (Dev only). | `false` |

### 3. Firebase Authentication
The backend uses Firebase Admin SDK to verify user identity tokens. 
- Ensure your Firebase Project ID matches your Google Cloud Project ID.
- The user's UID from the ID token is used to sandbox data under `gs://[BUCKET]/users/[UID]/`.

### Using Multi-User Isolation in Development
When running locally with `docker-compose` or `LocalStorageProvider`:
1.  **User Directories**: The system will automatically create directories in `backend/data/users/[UID]/`.
2.  **Mock Authentication**: To skip Firebase setup during local development, set `GRPC_AUTH_DISABLED=true`. The system will then use a default `dev-user` identity for all requests.
3.  **Manual Login**: If using real Firebase, the web client will handle the Google Login popup and pass the token to the backend.

## API Definition
See `protos/meetmanager/v1/meet_manager.proto` for the full Service definition.
# CI Trigger
