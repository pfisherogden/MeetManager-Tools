output "storage_bucket_name" {
  value = google_storage_bucket.data_bucket.name
}

output "artifact_registry_repo" {
  value = google_artifact_registry_repository.repo.name
}

output "service_account_email" {
  value = google_service_account.run_sa.email
}

output "backend_url" {
  value = google_cloud_run_v2_service.backend.uri
}

output "frontend_url" {
  value = google_cloud_run_v2_service.frontend.uri
}
