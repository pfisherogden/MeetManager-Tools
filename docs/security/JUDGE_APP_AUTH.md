# Judge App Authentication & Security

## Current Token Solution

The mm-tools system currently uses a static token-based authentication mechanism (`DATA_ACCESS_TOKEN`) to authorize the Stroke & Turn (S&T) Judge App to access meet data and sync Disqualifications (DQs). 

### How it works:
1. The `DATA_ACCESS_TOKEN` is configured as an environment variable on the `frontend` (Next.js) and `backend` (Python gRPC) Cloud Run services.
2. When an admin publishes a meet, the backend generates URLs containing the token as a query parameter (e.g., `/api/data?path=...&token=SECRET`).
3. These URLs are embedded in QR codes for the judges to scan.
4. The Next.js API routes (`/api/data` and `/api/sync-dqs`) validate the incoming `token` query parameter against the environment variable before proxying requests to the backend or serving data.

### Robustness Evaluation
**Strengths:**
- Simple to implement and use (no account creation required for volunteer judges).
- Easy to hand off via QR code.

**Weaknesses:**
- **URL Logging:** Tokens passed in URLs can be logged in browser history, proxy servers, or referer headers.
- **Global Scope:** A single token grants access to all currently published meets. If compromised, an attacker could potentially submit false DQs.
- **No Expiration:** The token does not automatically expire after the meet concludes.

### Conclusion on Robustness
The current solution is **adequate for low-stakes, temporary environments** (like a weekend swim meet), provided the token is kept secret and rotated periodically. However, it is **not robust enough for a permanent, highly secure production system**.

## Setup Instructions: Securing the Token in Google Cloud

To properly secure the `DATA_ACCESS_TOKEN` in your Cloud Run deployment, you should use **Google Cloud Secret Manager** rather than hardcoding it in your deployment files.

### Step-by-Step Configuration

1. **Enable Secret Manager API:**
   Ensure the Secret Manager API is enabled in your Google Cloud Project.
   ```bash
   gcloud services enable secretmanager.googleapis.com
   ```

2. **Create the Secret:**
   Create a new secret to store the token.
   ```bash
   gcloud secrets create MMTOOLS_DATA_ACCESS_TOKEN --replication-policy="automatic"
   ```

3. **Add the Secret Value:**
   Generate a strong, random string (e.g., using `openssl rand -hex 32`) and add it as a version to the secret.
   ```bash
   echo -n "your-super-strong-random-token-here" | gcloud secrets versions add MMTOOLS_DATA_ACCESS_TOKEN --data-file=-
   ```

4. **Grant Access to Cloud Run:**
   Your Cloud Run service account needs permission to access the secret. By default, Cloud Run uses the Compute Engine default service account (`PROJECT_NUMBER-compute@developer.gserviceaccount.com`).
   ```bash
   gcloud secrets add-iam-policy-binding MMTOOLS_DATA_ACCESS_TOKEN \
     --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
     --role="roles/secretmanager.secretAccessor"
   ```

5. **Update Deployment Configurations:**
   Modify your GitHub Actions deployment workflow (`.github/workflows/deploy-cloud-run.yml`) to pass the secret to your Cloud Run services.
   
   Instead of setting a plaintext environment variable, reference the secret:
   ```yaml
   env_vars: |
     # ... other vars
   secrets: |
     DATA_ACCESS_TOKEN=MMTOOLS_DATA_ACCESS_TOKEN:latest
   ```

## Future Revisions (Recommended)

To make the system truly robust in the future, we recommend transitioning from a static global token to **Short-Lived Signed JWTs (JSON Web Tokens)**:

1. **JWT Generation:** When the admin clicks "Publish", the backend signs a JWT using a secret key. The JWT payload includes the specific `meet_id` and an `exp` (expiration time, e.g., 24 hours).
2. **Handoff:** The JWT is embedded in the QR code URL.
3. **Validation:** The API routes verify the JWT signature and expiration.
4. **Benefit:** This scopes access to a single meet and ensures the link automatically expires after the event, mitigating the risks of URL logging and token leakage.
