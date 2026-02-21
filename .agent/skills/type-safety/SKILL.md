---
name: Type Safety & Protobuf
description: Best practices for handling Protobuf enums and type safety in Python and gRPC. Use when modifying protos or implementing service logic.
---

# Type Safety & Protobuf

## Protobuf Enums
- **Use Constants**: Always use generated enum constants (e.g., `pb2.MY_ENUM_VALUE`) instead of literal integers. Mypy treats them as distinct types.
- **Avoid Int Initialization**: Do not initialize enum-typed variables with `0`. Use the `_UNSPECIFIED` constant.
- **Fix Overload Errors**: Resolve `No overload variant` errors by ensuring dictionary keys use the exact enum type rather than `int`.

## gRPC Null Safety
- **Validate Requests**: Always add a `if request is None` guard at the entry of service methods.
- **Check Optional Fields**: Explicitly check if critical optional fields are set before access.
- **Safe Defaults**: Use the `or` operator or `getattr` with defaults for optional string/numeric fields.

## Tooling & Sync
- **Refresh Stubs**: Run `just codegen` if `mypy` or `ruff` report errors on recently modified proto definitions.
- **CI Sequence**: Ensure `codegen` runs before linting or type-checking in all CI pipelines.

