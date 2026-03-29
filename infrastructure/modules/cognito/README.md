# `cognito` Terraform module

Dedicated Cognito resources for API and admin SPA authentication:

- User pool for public users.
- Hosted UI app client configured for OAuth authorization code flow.
- User groups: `reader`, `editor`, `admin`.
- Hosted UI domain.

## Behavior

This module has no optional-resource fallbacks:

- `domain_prefix` must be set.
- `callback_urls` must be non-empty.
- `logout_urls` must be non-empty.

If these are missing, Terraform validation fails.

## Outputs

- `user_pool_id`
- `user_pool_issuer`
- `public_client_id`
