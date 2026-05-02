# Workflow: MeetManager-Tools

## Development Cycle (Research -> Strategy -> Execution)

1. **Research**: Systematically map the codebase and validate assumptions. Prioritize empirical reproduction of issues.
2. **Strategy**: Formulate a grounded plan based on research.
3. **Execution**: For each sub-task:
   - **Plan**: Define implementation approach and testing strategy.
   - **Act**: Apply targeted, surgical changes. Ensure idiomatically complete updates.
   - **Validate**: Run tests and workspace standards to confirm success.

## Coding Standards

### 1. General Principles
- **Idiomatic Quality**: Adhere to existing patterns (Tailwind, Shadcn UI, Async gRPC).
- **Type Safety**: Rigorous TypeScript and MyPy (Backend) usage.
- **Documentation**: Keep `ARCHITECTURE.md` and `conductor/` files up-to-date.

### 2. Testing
- **Backend**: `pytest` for unit and integration tests.
- **Frontend**: `Vitest` and `Playwright` (Planned E2E).
- **Mobile**: `Jest` for unit tests and manual journey verification.

### 3. Build & CI/CD
- Use `just` for all local automation.
- `just verify-ci` before every PR.
- Automated linting via `ruff` (Python) and `biome` (TypeScript).

## Git Flow

### 1. Branching Model
- **`main`**: Protected, production-ready branch.
- **Feature/Fix Branches**: All work happens in separate branches (e.g., `feat/auth`, `fix/mdb-parser`).
- **PR Requirement**: All changes must go through a PR and pass CI.

### 2. Pull Requests
- Provide clear context and evidence of verification (test results, screenshots).
- Link to relevant GitHub issues.

## Verification Checklist
- [ ] Code compiles without errors.
- [ ] All unit and integration tests pass.
- [ ] Linting and formatting checks pass (`just lint`).
- [ ] **Critical Journeys Verified**: Verified E2E for Ingestion, Reporting, Filtered Navigation, and Judge App Sync.
- [ ] **State Isolation Verified**: Confirmed no state leakage between test runs (explicit resets applied).
- [ ] `ARCHITECTURE_COMPREHENSIVE.md` and other documentation updated as needed.
- [ ] Learned behavior recorded in `GEMINI.md`.
