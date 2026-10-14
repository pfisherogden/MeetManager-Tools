# Enable APIs
resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "compute.googleapis.com",
    "artifactregistry.googleapis.com",
    "storage.googleapis.com",
    "iam.googleapis.com",
    "secretmanager.googleapis.com",
    "identitytoolkit.googleapis.com",
    "drive.googleapis.com",
    "drivepicker.googleapis.com"
  ])
  service            = each.key
  disable_on_destroy = false
}

# Artifact Registry for Container Images
resource "google_artifact_registry_repository" "repo" {
  location      = var.region
  repository_id = var.app_name
  description   = "Docker repository for MeetManager tools"
  format        = "DOCKER"
  depends_on    = [google_project_service.apis]

  cleanup_policy_dry_run = false

  cleanup_policies {
    id     = "delete-old-images"
    action = "DELETE"
    condition {
      tag_state  = "ANY"
      older_than = "1209600s"
    }
  }

  cleanup_policies {
    id     = "keep-latest-versions"
    action = "KEEP"
    most_recent_versions {
      keep_count = 3
    }
  }
}

# GCS Bucket for Dataset Storage
resource "google_storage_bucket" "data_bucket" {
  name          = "${var.app_name}-data-${var.project_id}"
  location      = var.region
  force_destroy = false

  uniform_bucket_level_access = true

  cors {
    origin          = var.custom_domain != "" ? ["https://${var.custom_domain}", "*"] : ["*"]
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

# IAM Role: Service Account Token Creator (Required for signed GCS URLs)
resource "google_project_iam_member" "run_sa_token_creator" {
  project = var.project_id
  role    = "roles/iam.serviceAccountTokenCreator"
  member  = "serviceAccount:${google_service_account.run_sa.email}"
}

# Backend Service (Cloud Run)
resource "google_cloud_run_v2_service" "backend" {
  name                = "${var.app_name}-backend"
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_ALL"
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
  name                = "${var.app_name}-frontend"
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_ALL"
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
        name  = "BACKEND_USE_SSL"
        value = "true"
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
        name  = "NEXT_PUBLIC_GOOGLE_CLIENT_ID"
        value = var.google_client_id
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

# Custom Domain Mapping via Global External Application Load Balancer (Option A)
resource "google_compute_global_address" "lb_ip" {
  count      = var.custom_domain != "" ? 1 : 0
  name       = "${var.app_name}-lb-ip"
  depends_on = [google_project_service.apis]
}

resource "google_compute_region_network_endpoint_group" "frontend_neg" {
  count                 = var.custom_domain != "" ? 1 : 0
  name                  = "${var.app_name}-frontend-neg"
  network_endpoint_type = "SERVERLESS"
  region                = var.region

  cloud_run {
    service = google_cloud_run_v2_service.frontend.name
  }

  depends_on = [google_project_service.apis]
}

resource "google_compute_region_network_endpoint_group" "backend_neg" {
  count                 = var.custom_domain != "" ? 1 : 0
  name                  = "${var.app_name}-backend-neg"
  network_endpoint_type = "SERVERLESS"
  region                = var.region

  cloud_run {
    service = google_cloud_run_v2_service.backend.name
  }

  depends_on = [google_project_service.apis]
}

resource "google_compute_backend_service" "frontend_lb" {
  count                 = var.custom_domain != "" ? 1 : 0
  name                  = "${var.app_name}-frontend-lb"
  protocol              = "HTTPS"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  enable_cdn            = var.enable_cdn

  backend {
    group = google_compute_region_network_endpoint_group.frontend_neg[0].id
  }

  depends_on = [google_project_service.apis]
}

resource "google_compute_backend_service" "backend_lb" {
  count                 = var.custom_domain != "" ? 1 : 0
  name                  = "${var.app_name}-backend-lb"
  protocol              = "HTTP2"
  load_balancing_scheme = "EXTERNAL_MANAGED"

  backend {
    group = google_compute_region_network_endpoint_group.backend_neg[0].id
  }

  depends_on = [google_project_service.apis]
}

resource "google_compute_url_map" "https_url_map" {
  count           = var.custom_domain != "" ? 1 : 0
  name            = "${var.app_name}-https-url-map"
  default_service = google_compute_backend_service.frontend_lb[0].id

  host_rule {
    hosts        = [var.custom_domain]
    path_matcher = "allpaths"
  }

  path_matcher {
    name            = "allpaths"
    default_service = google_compute_backend_service.frontend_lb[0].id

    path_rule {
      paths   = ["/meetmanager.v1.MeetManagerService/*", "/api/grpc/*"]
      service = google_compute_backend_service.backend_lb[0].id
    }
  }
}

resource "google_compute_managed_ssl_certificate" "lb_cert" {
  count = var.custom_domain != "" ? 1 : 0
  name  = "${var.app_name}-ssl-cert"

  managed {
    domains = [var.custom_domain]
  }

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [google_project_service.apis]
}

resource "google_compute_target_https_proxy" "https_proxy" {
  count            = var.custom_domain != "" ? 1 : 0
  name             = "${var.app_name}-https-proxy"
  url_map          = google_compute_url_map.https_url_map[0].id
  ssl_certificates = [google_compute_managed_ssl_certificate.lb_cert[0].id]
}

resource "google_compute_global_forwarding_rule" "https_forwarding_rule" {
  count                 = var.custom_domain != "" ? 1 : 0
  name                  = "${var.app_name}-https-forwarding-rule"
  target                = google_compute_target_https_proxy.https_proxy[0].id
  port_range            = "443"
  ip_protocol           = "TCP"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  ip_address            = google_compute_global_address.lb_ip[0].id
}

resource "google_compute_url_map" "http_redirect" {
  count = var.custom_domain != "" ? 1 : 0
  name  = "${var.app_name}-http-redirect"

  default_url_redirect {
    https_redirect         = true
    redirect_response_code = "MOVED_PERMANENTLY_DEFAULT"
    strip_query            = false
  }
}

resource "google_compute_target_http_proxy" "http_proxy" {
  count   = var.custom_domain != "" ? 1 : 0
  name    = "${var.app_name}-http-proxy"
  url_map = google_compute_url_map.http_redirect[0].id
}

resource "google_compute_global_forwarding_rule" "http_forwarding_rule" {
  count                 = var.custom_domain != "" ? 1 : 0
  name                  = "${var.app_name}-http-forwarding-rule"
  target                = google_compute_target_http_proxy.http_proxy[0].id
  port_range            = "80"
  ip_protocol           = "TCP"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  ip_address            = google_compute_global_address.lb_ip[0].id
}

