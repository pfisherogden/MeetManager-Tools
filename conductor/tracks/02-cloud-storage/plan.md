# Plan: [Phase 2] User-Sandboxed Data Storage & Management

## Objective
Implement data isolation using Google Cloud Storage (GCS) and an abstract storage layer to allow per-user file management in a cloud environment.

## Requirements
- **Storage Abstraction**: Abstract `StorageProvider` in the Python backend.
- **Local Storage Provider**: File-based storage for local development.
- **GCS Storage Provider**: Bucket-based storage for production.
- **Isolation**: UID-based paths (`users/[UID]/...`).
- **Dataset Loader**: Update to support per-user storage and listing.

## Implementation Steps

### 1. Storage Abstraction
- [ ] Create `backend/src/storage_provider.py` with an abstract base class.
- [ ] Implement `LocalStorageProvider` (current functionality).
- [ ] Implement `GCSStorageProvider` using the `google-cloud-storage` library.
- [ ] Update `server.py` and `dataset_loader.py` to use the `StorageProvider` interface.

### 2. Multi-User Dataset Loading
- [ ] Update `UploadDataset` logic to include the authenticated `uid` in the storage path.
- [ ] Update `ListDatasets` logic to filter files by the user's `uid` prefix in GCS.
- [ ] Update `GenerateReportBundle` to store results in user-specific temporary directories.

## Verification Strategy
- **Unit Test (Backend)**: Verify `StorageProvider` implementations using mocks for the file system and GCS API.
- **Integration Test**: Verify that uploading a dataset as User A does not show it in the list for User B.
