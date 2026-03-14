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

variable "firebase_api_key" {
  description = "Firebase API Key"
  type        = string
  sensitive   = true
}

variable "firebase_messaging_sender_id" {
  description = "Firebase Messaging Sender ID"
  type        = string
}

variable "firebase_app_id" {
  description = "Firebase App ID"
  type        = string
}
