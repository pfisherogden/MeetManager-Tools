# Plan: [Phase 1] Multi-User Authentication & User Context

## Objective
Implement secure multi-user authentication using Firebase and ensure that the user identity is passed from the web client to the backend for every request.

## Requirements
- **Firebase Project**: Setup Firebase project with Google Login enabled.
- **Web Client**: `AuthContext` provider in Next.js.
- **Web Client**: Middleware to inject ID token into gRPC-web metadata.
- **Backend**: `firebase-admin` integration for token verification.
- **Backend**: gRPC interceptor to extract `user_id` and inject into context.

## Implementation Steps

### 1. Firebase Client Setup
- [ ] Initialize Firebase SDK in `web-client`.
- [ ] Create `AuthContext.tsx` to manage user state (loading, user, logout).
- [ ] Implement Google Login flow.
- [ ] Update `web-client/lib/mm-client.ts` to fetch the current ID token and add it as a `Authorization: Bearer <token>` header to all gRPC calls.

### 2. Backend JWT Verification
- [ ] Add `firebase-admin` to `backend/pyproject.toml`.
- [ ] Create `backend/src/auth_interceptor.py`.
- [ ] Implement `AsyncServerInterceptor` to:
    - Extract Bearer token from metadata.
    - Verify token using `auth.verify_id_token`.
    - Extract `uid` and store in `context`.
    - Reject unauthenticated requests to protected methods.
- [ ] Update `server.py` to use the new interceptor.

## Verification Strategy
- **Unit Test (Backend)**: Mock `firebase-admin` and verify the interceptor correctly extracts and validates the UID.
- **Manual Test**: Log in via the web client, perform an action, and verify the backend logs show the correct UID.
