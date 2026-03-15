# Cloud Deployment Standards

This skill provides procedures for deploying MMTools services to Google Cloud Run with proper authentication and security.

## 1. Authentication (Firebase)
### Build-Time Configuration
- **Critical**: Next.js `NEXT_PUBLIC_` environment variables MUST be available at **build time** to be included in the client-side bundle.
- **Environment Parity**: For consistency, also provide these variables as **runtime** environment variables in the Cloud Run service definition. This ensures that any server-side code (SSR/Server Actions) can also access them correctly.
- **Procedure**: 
  1. Define `ARG` in the `Dockerfile` for each Firebase variable.
  2. Map `ARG` to `ENV` in the `Dockerfile`.
  3. Pass values via `--build-arg` in the build step of the CI/CD pipeline.
  4. Provide the same values in the `env_vars` section of the deployment step.

### Identity Toolkit
- **Requirement**: The `identitytoolkit.googleapis.com` API must be enabled in the GCP project for Firebase Auth to function.

## 3. gRPC Security
- **Cloud Communication**: When connecting to a Cloud Run service via gRPC, use **SSL/TLS**.
- **Detection**: Use `ChannelCredentials.createSsl()` if the hostname contains `.run.app`.
- **Formatting**: Strip `https://` from the host URL before passing it to the gRPC client.

## 4. Public Accessibility
- **Command**: Deploy with the `--allow-unauthenticated` flag to ensure the service is reachable by the public internet.
- **Workflow**: Ensure this flag is present in `.github/workflows/deploy-cloud-run.yml`.
