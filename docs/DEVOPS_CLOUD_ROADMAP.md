# 📊 MeetManager-Tools: DevOps & Cloud Deployment Roadmap

## 1. Current State Analysis
MeetManager-Tools is a robust application with a modern tech stack (Next.js, Python/gRPC) and containerized local development. However, it currently lacks multi-user isolation and a production-ready cloud deployment strategy.

### Strengths:
- **Layered Dockerfiles:** Good use of multi-stage builds and dependency caching.
- **Task Automation:** `Justfile` provides a consistent interface for developers.
- **Standalone Frontend:** Optimized production image size.

---

## 2. Multi-User Architecture & Security
To support multiple users online, we must transition from a "local file" model to a "user-sandboxed" model.

### A. Identity & Authentication (Firebase)
- **Integration:** Use **Firebase Authentication** with Google Sign-In. It's lightweight and integrates perfectly with Next.js.
- **Client-Side:** Frontend uses the Firebase SDK to manage user sessions and JWT tokens.
- **Backend:** The Python gRPC server will intercept the `Authorization: Bearer <token>` header, using the `firebase-admin` SDK to verify the user's UID.

### B. Data Isolation (Sandboxing)
- **Storage:** Use **Google Cloud Storage (GCS)** instead of a local `data/` folder.
- **Isolation Strategy:** 
  - Store files in a bucket using the path structure: `gs://[BUCKET_NAME]/users/[USER_ID]/datasets/[DATASET_ID].mdb`.
  - Use **GCS Uniform Bucket-Level Access** combined with IAM or Signed URLs to ensure users can only access their own prefix.
- **In-Memory Cache:** Update the backend `dataset_loader.py` to be user-aware, caching datasets keyed by `(user_id, dataset_id)`.

---

## 3. Cloud Deployment Strategy: Google Cloud Run

### Recommended Infrastructure:
1.  **Frontend:** Cloud Run service (Next.js).
2.  **Backend:** Cloud Run service (Python/gRPC).
3.  **Storage:** Google Cloud Storage for MDB/JSON files.
4.  **Database:** Firestore (optional) to store user metadata, dataset names, and sharing settings.

---

## 4. Roadmap & Task List

### Phase 1: Authentication & User Context
- [ ] **Task:** Set up Firebase Project and enable Google Auth.
- [ ] **Task:** Implement `AuthContext` in Next.js frontend.
- [ ] **Task:** Add gRPC Interceptor in Python to verify Firebase JWTs.

### Phase 2: User-Sandboxed Storage
- [ ] **Task:** Abstract filesystem operations in the backend to support GCS.
- [ ] **Task:** Update upload logic to save files to `users/[UID]/...`.
- [ ] **Task:** Implement dataset listing filtered by the authenticated UID.

### Phase 3: Deployment & Infrastructure (IaC)
- [ ] **Task:** Create Terraform scripts for Cloud Run, GCS, and Artifact Registry.
- [ ] **Task:** Set up CI/CD to build and deploy images on merge to `main`.

---

## 5. Agent Prompts for Implementation

### Prompt: Auth Integration (Next.js + Firebase)
> "Implement Firebase Authentication in the Next.js client. Create an `AuthContext` provider that manages the user state. Update the gRPC client factory to automatically include the user's ID token in the metadata for every request."

### Prompt: Backend JWT Verification
> "Implement a gRPC interceptor in the Python backend using `firebase-admin`. The interceptor should extract the Bearer token from the metadata, verify it, and inject the `user_id` into the request context. Reject any unauthenticated requests to protected endpoints."

### Prompt: GCS Storage Abstraction
> "Refactor the backend storage logic to use an abstract `StorageProvider`. Implement two providers: `LocalStorageProvider` (for dev) and `GCSStorageProvider` (for production). The GCS provider should use the user's UID to isolate file access."

---
