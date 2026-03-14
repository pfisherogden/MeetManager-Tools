# Enable APIs
resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "storage.googleapis.com",
    "iam.googleapis.com",
    "secretmanager.googleapis.com"
  ])
  service = each.key
  disable_on_destroy = false
}

# Artifact Registry for Container Images
resource "google_artifact_registry_repository" "repo" {
  location      = var.region
  repository_id = var.app_name
  description   = "Docker repository for MeetManager tools"
  format        = "DOCKER"
  depends_on    = [google_project_service.apis]
}

# GCS Bucket for Dataset Storage
resource "google_storage_bucket" "data_bucket" {
  name          = "${var.app_name}-data-${var.project_id}"
  location      = var.region
  force_destroy = false

  uniform_bucket_level_access = true

  cors {
    origin          = ["*"] # Adjust this to your frontend URL later
    method          = ["GET", "HEAD", "PUT", "POST", "DELETE"]
    response_header = ["*"]
    max_age_seconds = 3600
  }
  
  depends_on = [google_project_service.apis]
}

# Service Account for Cloud Run
resource "google_service_account" "run_sa" {
  account_id   = "${var.app_name}-runner"
  display_name = "Cloud Run Service Account for ${var.app_name}"
}

# IAM Role: Storage Object Admin for the Bucket
resource "google_storage_bucket_iam_member" "storage_admin" {
  bucket = google_storage_bucket.data_bucket.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.run_sa.email}"
}

# Backend Service (Cloud Run)
resource "google_cloud_run_v2_service" "backend" {
  name     = "${var.app_name}-backend"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"
  deletion_protection = false

  template {
    service_account = google_service_account.run_sa.email
    containers {
      image = "us-docker.pkg.dev/cloudrun/container/hello" # Placeholder
      ports {
        container_port = 8080
      }
      env {
        name  = "GCS_BUCKET_NAME"
        value = google_storage_bucket.data_bucket.name
      }
      env {
        name  = "GRPC_AUTH_DISABLED"
        value = "false"
      }
    }
  }

  depends_on = [google_project_service.apis]
}

# Frontend Service (Cloud Run)
resource "google_cloud_run_v2_service" "frontend" {
  name     = "${var.app_name}-frontend"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"
  deletion_protection = false

  template {
    service_account = google_service_account.run_sa.email
    containers {
      image = "us-docker.pkg.dev/cloudrun/container/hello" # Placeholder
      ports {
        container_port = 3000
      }
      env {
        name  = "BACKEND_INTERNAL_HOST"
        value = replace(google_cloud_run_v2_service.backend.uri, "https://", "")
      }
      env {
        name  = "NEXT_PUBLIC_FIREBASE_API_KEY"
        value = var.firebase_api_key
      }
      env {
        name  = "NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN"
        value = "${var.project_id}.firebaseapp.com"
      }
      env {
        name  = "NEXT_PUBLIC_FIREBASE_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET"
        value = "${var.project_id}.firebasestorage.app"
      }
      env {
        name  = "NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID"
        value = var.firebase_messaging_sender_id
      }
      env {
        name  = "NEXT_PUBLIC_FIREBASE_APP_ID"
        value = var.firebase_app_id
      }
      env {
        name  = "NEXT_PUBLIC_AUTH_DISABLED"
        value = "false"
      }
      env {
        name  = "FRONTEND_PUBLIC_URL"
        value = google_cloud_run_v2_service.frontend.uri
      }
    }
  }

  depends_on = [google_project_service.apis]
}

# IAM: Allow unauthenticated access to frontend (public web)
resource "google_cloud_run_v2_service_iam_member" "frontend_public" {
  name     = google_cloud_run_v2_service.frontend.name
  location = google_cloud_run_v2_service.frontend.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# IAM: Allow unauthenticated access to backend (for now, will use JWT)
resource "google_cloud_run_v2_service_iam_member" "backend_public" {
  name     = google_cloud_run_v2_service.backend.name
  location = google_cloud_run_v2_service.backend.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}
