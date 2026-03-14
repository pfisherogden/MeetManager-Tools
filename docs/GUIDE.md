# Developer & Deployment Guide

This guide covers the core workflows for developing locally and deploying to the cloud.

## 1. Local Development

### Prerequisites
- Docker & Docker Compose
- Node.js v20
- Python 3.11+ (via `uv` recommended)
- `just` task runner

### Quick Start
1. **Initial Setup**:
   ```bash
   npm install
   just codegen
   ```
2. **Start Services**:
   ```bash
   just up
   ```
   The web client will be available at `http://localhost:3000`.

3. **Run Tests**:
   ```bash
   just test           # Run all unit tests
   just test-journeys  # Run headless end-to-end integration tests
   ```

### Shared Machine Safety
If running on a machine with multiple active workspaces:
- Set `COMPOSE_PROJECT_NAME` in your `.env` file to a unique value.
- Override host ports using `FRONTEND_PORT` and `BACKEND_PORT`.

---

## 2. Cloud Deployment (GCP)

### Architecture
The application is deployed to **Google Cloud Run** using a fully automated CI/CD pipeline.
- **Frontend**: Next.js (Standalone mode)
- **Backend**: Python gRPC Server
- **Storage**: User-sandboxed GCS Buckets
- **Container Registry**: Artifact Registry

### CI/CD Workflow
1. Push changes to the `main` branch.
2. GitHub Actions (`deploy-cloud-run.yml`) builds the Docker images.
3. Images are pushed to the Artifact Registry.
4. Services are deployed to Cloud Run with updated environment variables.

### Manual Infrastructure Updates
Infrastructure is managed via **Terraform** in the `deploy/` directory.
To apply changes manually:
```bash
cd deploy
terraform init
terraform apply
```

---

## 3. User Journeys

### Meet Director Workflow
1. Navigate to the **Admin** section.
2. Upload an `.mdb` file.
3. Verify stats on the **Dashboard**.
4. Generate reports in the **Reports** section.

### Judge Workflow
1. Click **Publish to Judge App** in the Admin/Dashboard.
2. Scan the generated QR code or open the link.
3. Record DQs in the mobile app.
4. Click **Sync** to push DQs back to the backend.
