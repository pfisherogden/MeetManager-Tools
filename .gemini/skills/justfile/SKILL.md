---
name: Justfile Management
description: Best practices for writing and maintaining Justfiles in this project.
---
# Justfile Management

## Principles
- **Separation of Concerns**: Keep "checks" (lint, type-check) separate from "fixes" (format, fix). This ensures CI can run in a non-modifying mode.
- **Dependency Graph**: Use `just` dependencies (e.g., `test: codegen lint`) to ensure prerequisites are met without redundant commands.
- **Hermeticity**: Recipes should ideally work the same in Docker and locally. Use `just verify-ci` to verify local changes in a container.

## Recipe Patterns
### Linting vs Fixing
Always provide a read-only `lint` recipe and a modifying `fix` recipe.
```just
# Read-only checks
lint: lint-backend lint-frontend type-check

# Modifying fixes
fix: fix-backend fix-frontend
```

### Code Generation
Recipes that depend on generated code (like gRPC) must depend on the `codegen` recipe.
```just
type-check: codegen
    uv run mypy src
```

### Cleanup
Provide a `clean` recipe to remove temporary files, caches, and build artifacts.
```just
clean:
    -rm -rf .tmp .npm_cache backend/src/__pycache__ web-client/.next
```

## Best Practices
- **Quiet Mode**: Use `@` before commands to suppress echoing the command string if it's too noisy.
- **Fail Fast**: Chain commands with `&&` if they are part of the same logical step.
- **Shell Selection**: Always set `set shell := ["bash", "-c"]` at the top for consistent cross-platform behavior.
- **Environment Variables**: Prefix commands with necessary env vars (e.g., `MYPYPATH=src`) to avoid global environment pollution.
