# API Authentication and Key Operations

> **Status**: stable
> **Scope**: Public API authn/authz, Cognito JWT validation, machine API key lifecycle
> **Last updated**: 2026-03-29 (promoted to stable; implemented in services/api)

---

## Authentication modes

The API accepts two credential types:

- **Public users**: `Authorization: Bearer <jwt>` from the newsroom Cognito user pool.
- **Machine clients**: `X-API-Key: sk_...` keys issued by API admins.

All requests are normalized into one internal `AuthContext`:

- `subject`
- `caller_type` (`user` or `machine`)
- `roles`
- `scopes`
- `key_id` (machine callers only)

## Authorization model

Role-based policy is enforced at route dependencies:

- `reader`: read-only endpoints.
- `editor`: reader plus write access for `sources` and `assignments`, and artifact patch.
- `admin`: all editor permissions plus `agent-configs` write/delete and machine key management.
- `machine`: explicit allow only; default deny.

## Cognito runtime configuration

API service environment variables:

- `COGNITO_REGION`
- `COGNITO_USER_POOL_ID`
- `COGNITO_ISSUER`
- `COGNITO_AUDIENCE`

JWT verification uses Cognito JWKS and validates:

- signature (`RS256`)
- `iss` claim
- `aud` claim
- token expiration

Roles are read from `cognito:groups`.

## Admin SPA (Cognito Hosted UI)

The `admin` app signs in via Cognito Hosted UI (OAuth authorization code + PKCE) and signs out via the Hosted UI logout endpoint. It uses path-based routes (`BrowserRouter`); the Cognito app client must allow:

- **Callback URL**: same value as `VITE_REDIRECT_URI` (e.g. `https://admin.example.com/callback`).
- **Sign out URL**: same value as `VITE_LOGOUT_URI` (typically the SPA origin, e.g. `https://admin.example.com/`).

Terraform maps these to `newsroom_cognito_callback_urls` and `newsroom_cognito_logout_urls` in the dedicated Cognito module (`infrastructure/modules/cognito`).

## API key lifecycle

`api_clients` table stores only hashed keys (`key_hash`) and a non-sensitive `key_prefix`.
Plaintext key material is returned once at issuance.

Lifecycle operations:

1. **Issue** (`POST /api-clients`) creates a new active key.
2. **Rotate** (`POST /api-clients/{id}/rotate`) revokes old key and creates replacement.
3. **Revoke** (`POST /api-clients/{id}/revoke`) disables key immediately.

Recommended operational policy:

- rotate keys every 90 days
- set `expires_at` on all machine keys
- keep key roles/scopes narrow
- revoke immediately on suspected exposure

## Verification checklist

1. Create users in Cognito groups: `reader`, `editor`, `admin`.
2. Acquire JWT and call a protected read endpoint.
3. Verify write endpoint is blocked for `reader`.
4. Issue a machine key via admin endpoint.
5. Call API with `X-API-Key`; verify access.
6. Revoke key and confirm calls fail with `401`.

---

## Decision log

| Date | Change | Rationale |
|------|--------|-----------|
| 2026-03-23 | Documented Cognito callback vs logout URLs for the admin SPA | Aligns infra (`callback_urls` / `logout_urls`) with `VITE_REDIRECT_URI` and `VITE_LOGOUT_URI` |
| 2026-03-23 | Moved Cognito infra into a dedicated module with required domain/callback/logout inputs | Eliminates optional-resource fallbacks so auth infra either provisions fully or fails validation |
