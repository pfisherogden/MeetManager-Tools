"""Unit tests for Cloud Run custom domain Terraform configuration (Issue #169)."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEPLOY_DIR = REPO_ROOT / "deploy"


def test_terraform_custom_domain_variables_defined() -> None:
    """Verify custom_domain and enable_cdn variables exist in deploy/variables.tf."""
    variables_tf = (DEPLOY_DIR / "variables.tf").read_text(encoding="utf-8")
    assert 'variable "custom_domain"' in variables_tf
    assert 'variable "enable_cdn"' in variables_tf


def test_terraform_custom_domain_load_balancer_resources() -> None:
    """Verify Global External Application Load Balancer, NEGs, SSL cert, and HTTP->HTTPS redirect exist."""
    main_tf = (DEPLOY_DIR / "main.tf").read_text(encoding="utf-8")
    assert '"compute.googleapis.com"' in main_tf
    assert 'resource "google_compute_global_address" "lb_ip"' in main_tf
    assert 'resource "google_compute_region_network_endpoint_group" "frontend_neg"' in main_tf
    assert 'resource "google_compute_region_network_endpoint_group" "backend_neg"' in main_tf
    assert 'resource "google_compute_backend_service" "frontend_lb"' in main_tf
    assert 'resource "google_compute_backend_service" "backend_lb"' in main_tf
    assert 'protocol              = "HTTP2"' in main_tf
    assert 'resource "google_compute_url_map" "https_url_map"' in main_tf
    assert '"/meetmanager.v1.MeetManagerService/*"' in main_tf
    assert 'resource "google_compute_managed_ssl_certificate" "lb_cert"' in main_tf
    assert "create_before_destroy = true" in main_tf
    assert 'resource "google_compute_target_https_proxy" "https_proxy"' in main_tf
    assert 'resource "google_compute_global_forwarding_rule" "https_forwarding_rule"' in main_tf
    assert 'resource "google_compute_url_map" "http_redirect"' in main_tf
    assert 'resource "google_compute_target_http_proxy" "http_proxy"' in main_tf
    assert 'resource "google_compute_global_forwarding_rule" "http_forwarding_rule"' in main_tf


def test_terraform_custom_domain_outputs_and_ssl_env() -> None:
    """Verify custom_domain_url and load_balancer_ip outputs and BACKEND_USE_SSL env configuration."""
    outputs_tf = (DEPLOY_DIR / "outputs.tf").read_text(encoding="utf-8")
    assert 'output "custom_domain_url"' in outputs_tf
    assert 'output "load_balancer_ip"' in outputs_tf

    main_tf = (DEPLOY_DIR / "main.tf").read_text(encoding="utf-8")
    assert 'name  = "BACKEND_USE_SSL"' in main_tf

    mm_client_ts = (REPO_ROOT / "web-client" / "lib" / "mm-client.ts").read_text(encoding="utf-8")
    assert 'targetHost.startsWith("https://")' in mm_client_ts
