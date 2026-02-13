---
name: Type Safety & Protobuf
description: Best practices for handling Protobuf enums and type safety in Python.
---
# Type Safety & Protobuf

## Mypy & Protobuf Enums
- **Type Mismatch**: Mypy treats Protobuf enums as distinct types, not just integers.
- **Initialization**: Never initialize an enum variable with `0` or other literal integers if it will be used in a dictionary lookup where keys are the enum type.
- **Correct Usage**: Always use the generated enum constant (e.g., `pb2.REPORT_TYPE_PSYCH_UNSPECIFIED`) for initialization and comparison.
- **Overload Variants**: If you see `No overload variant of "get" of "dict" matches argument types "int", "str"`, it's usually because the key type is an enum and you provided an `int`.

## Null Safety in gRPC
- **Optional Fields**: Protobuf 3 fields are optional by default. Always check if a field is set if it's critical.
- **None Requests**: In Python gRPC implementations, always add a guard for `request is None` at the beginning of service methods, or ensure default values are used.
- **Example**:
  ```python
  def MyMethod(self, request, context):
      if request is None:
          # Use defaults or return error
          return pb2.MyResponse(success=False, message="Missing request")
      
      title = request.title or "Default Title"
      # ...
  ```

## Code Generation
- **Local Staleness**: If `mypy` or `ruff` report errors in files that seem correct, run `just codegen` to ensure local stubs (`.pyi`) and generated code are in sync with `protos/`.
- **CI Dependency**: CI workflows must run `codegen` before any linting or testing steps that import the `meetmanager.v1` package.
