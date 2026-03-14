variable "project_id" {
  description = "The GCP Project ID"
  type        = string
  default     = "mmtools-488404"
}

variable "region" {
  description = "The GCP region for deployment"
  type        = string
  default     = "us-west1"
}

variable "app_name" {
  description = "The name of the application"
  type        = string
  default     = "mmtools"
}
