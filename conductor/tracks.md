# Tracks Registry: MeetManager-Tools

This registry tracks the major workstreams (Tracks) for the MeetManager-Tools cloud migration and multi-user support project.

| ID | Title | Status | Link |
|:---|:---|:---|:---|
| `01-multi-user-auth` | [Phase 1] Multi-User Authentication & User Context | ✅ Completed | [Plan](./tracks/01-multi-user-auth/plan.md) |
| `02-cloud-storage` | [Phase 2] User-Sandboxed Data Storage & Management | ✅ Completed | [Plan](./tracks/02-cloud-storage/plan.md) |
| `03-cloud-run-deployment` | [Phase 3] Automated Cloud Infrastructure & CI/CD | 🟡 In Progress | [Plan](./tracks/03-cloud-run-deployment/plan.md) |

## Track Descriptions

### 01-multi-user-auth
Introduction of identity to the application using Firebase. Includes setting up the Firebase SDK in the Next.js client and implementing a gRPC interceptor in the Python backend to verify user tokens.

### 02-cloud-storage
Data isolation so that users only see their own files. Includes refactoring the backend to support an abstract `StorageProvider` and updating the dataset loader to use GCS with user-specific paths.

### 03-cloud-run-deployment
Automation of infrastructure and deployment. Includes Terraform scripts for provisioning GCP resources (Cloud Run, GCS) and updating GitHub Actions for automated builds and deployments.
