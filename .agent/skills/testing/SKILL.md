---
name: Testing Standards
description: Guidelines for running and writing tests in this project.
---
# Testing Standards

## General
- **Requirement**: Always create or update tests for new features. Verifying code effectively is a hard requirement.

## Frontend (web-client)
- **Tool**: Vitest
- **Command**: `npm test` or `npm run test`
- **Scope**: Ensure components and logic are covered.

## Backend (backend)
- **Tool**: pytest
- **Alternative**: Integration checks can leverage `test_client.py` pattern if needed, but proper pytest suites are preferred.
