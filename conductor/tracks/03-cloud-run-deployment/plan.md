# Plan: [Phase 3] Automated Cloud Infrastructure & CI/CD

## Objective
Automate the provisioning and deployment of the application to Google Cloud Run, ensuring a scalable and cost-effective cloud environment.

## Requirements
- **Infrastructure as Code (Terraform)**: For provisioning GCP resources (Cloud Run, GCS, IAM).
- **Artifact Registry**: Docker repository for backend and frontend images.
- **Continuous Deployment (GitHub Actions)**: Automatic builds and deployments on push to `main`.
- **Environment Variables**: Manage sensitive keys (Firebase, GCS bucket) securely using Secret Manager.

## Implementation Steps

### 0. Cloud-Ready Backend Preparation
- [x] **Port Normalization**: Update `server.py` to use `PORT` env var.
- [x] **gRPC Health Check**: Implement standard health servicer.
- [x] **Container Optimization**: Refine `backend/Dockerfile` for Cloud Run.

### 1. Infrastructure as Code (Terraform)
- [x] Create `deploy/` directory with Terraform configuration (`main.tf`, `variables.tf`).
- [x] Define resources:
    - GCS Bucket for data storage.
    - Artifact Registry for container images.
    - Cloud Run services (Backend and Web Client).
    - Service Accounts with least-privilege IAM roles.
    - Secret Manager for sensitive environment variables.
- [x] Output service URLs for use in the application configuration.

### 2. Continuous Deployment Pipeline
- [x] Create `.github/workflows/cd.yml`.
- [x] Configure `google-github-actions/auth` and `google-github-actions/setup-gcloud`.
- [x] Update build steps for:
    - Building backend image and pushing to Artifact Registry.
    - Building web-client image and pushing to Artifact Registry.
    - Deploying both to Cloud Run using `google-github-actions/deploy-cloudrun`.

### 3. Identity & Secure Communication
- [x] **Secure gRPC**: Update `mm-client.ts` to use SSL/TLS for Cloud Run backend connections.
- [x] **Authentication**: Implement Firebase Google Login and AuthGuard to protect data.
- [x] **Renaming**: Transition to `mmtools` naming for all cloud resources and project references.

## Verification Strategy
- **Local Test**: Run `just up` and `just test-journeys` 3 times consecutively (Passed).
- **Deployment Test**: Push to branch, verify GitHub Actions CD pipeline (Passed Run #23089841152).
- **End-to-End Test**: Verify frontend and backend accessible at Cloud Run URLs (Verified).
