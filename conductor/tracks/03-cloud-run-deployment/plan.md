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
- [ ] Create `deploy/` directory with Terraform configuration (`main.tf`, `variables.tf`).
- [ ] Define resources:
    - GCS Bucket for data storage.
    - Artifact Registry for container images.
    - Cloud Run services (Backend and Web Client).
    - Service Accounts with least-privilege IAM roles.
    - Secret Manager for sensitive environment variables.
- [ ] Output service URLs for use in the application configuration.

### 2. Continuous Deployment Pipeline
- [ ] Create `.github/workflows/cd.yml`.
- [ ] Configure `google-github-actions/auth` and `google-github-actions/setup-gcloud`.
- [ ] Update build steps for:
    - Building backend image and pushing to Artifact Registry.
    - Building web-client image and pushing to Artifact Registry.
    - Deploying both to Cloud Run using `google-github-actions/deploy-cloudrun`.

## Verification Strategy
- **Infrastructure Test**: Run `terraform plan` and verify resource creation locally.
- **Deployment Test**: Push a small change to a branch, verify the CI/CD pipeline triggers, builds, and deploys successfully.
- **End-to-End Test**: Verify the application is accessible and functional at the generated Cloud Run URL.
