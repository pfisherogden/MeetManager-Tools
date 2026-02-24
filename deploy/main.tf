# Enable APIs
resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "storage.googleapis.com",
    "iam.googleapis.com"
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
