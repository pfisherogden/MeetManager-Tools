# Test Suite & Fixtures

This directory contains the comprehensive test suite for MeetManager Tools.

## Fixture Strategy

To ensure CI stability and reproducibility without requiring access to proprietary `.mdb` files, we use **Anonymized JSON Fixtures**.

- **Location**: `tests/fixtures/anonymized_meets/`
- **Source of Truth**: These JSON files are generated from real `.mdb` data but have athlete names and sensitive info anonymized.
- **CI Eligibility**: All reporting and extraction tests MUST use these fixtures if they need to run in GitHub Actions.

## Test Categories

1.  **Unit Tests**: Located in `backend/tests` and `web-client` (Vitest).
2.  **Integration Tests**: Located in `tests/integration`.
3.  **Reporting Tests**: Use the `MmToJsonConverter` with JSON `table_data` directly to verify PDF layout and data accuracy.

## Reliability Standards

- **5-Cycle Verification**: Always run `just test-backend` 5 times after major logic changes to catch intermittent issues.
- **Pre-Commit**: The `just pre-commit` command in the root is the mandatory entry point for verification.
