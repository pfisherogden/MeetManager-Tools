// Shim for TypeScript resolution
// This file is used when the bundler doesn't automatically pick up .web.ts or .native.ts
// We default to web implementation for now (or could just throw errors)

export * from "./db.web";
