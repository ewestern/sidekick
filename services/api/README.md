# API service

FastAPI service for Sidekick editorial/admin APIs.

## Run locally

From repo root:

```bash
cd services/api
uv run sidekick-api
```

When started via the CLI, the service automatically loads a local `.env` file (if present) using `python-dotenv`, without overriding already-exported shell variables.

## Environment variables

The API service reads these environment variables:

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `DATABASE_URL` | Yes | `""` | SQLAlchemy connection URL used by the API and migration startup hook. |
| `COGNITO_REGION` | Conditional* | `""` | AWS region used to build the Cognito JWKS URL. |
| `COGNITO_USER_POOL_ID` | Conditional* | `""` | Cognito User Pool ID used with `COGNITO_REGION` to build the JWKS URL. |
| `COGNITO_ISSUER` | Conditional* | `""` | Fallback issuer URL used to build the JWKS URL when region/pool is not set. |
| `COGNITO_AUDIENCE` | Conditional* | `""` | JWT audience for bearer-token validation. |
| `API_KEY_PEPPER` | Yes | `""` | Pepper used when hashing API keys for storage/verification. |
| `CORS_ALLOWED_ORIGINS` | No | `http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173` | Comma-separated list of allowed browser origins for CORS preflight/requests. |

\* Required when authenticating with Cognito JWT bearer tokens. If you only use API key auth for local development, Cognito variables are not required for those requests.

## Local `.env` example

```dotenv
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/sidekick
API_KEY_PEPPER=replace-me

# Only needed for Cognito bearer-token auth flows:
COGNITO_REGION=us-west-2
COGNITO_USER_POOL_ID=us-west-2_example
COGNITO_AUDIENCE=example_client_id
# Optional if REGION + USER_POOL_ID are set:
COGNITO_ISSUER=https://cognito-idp.us-west-2.amazonaws.com/us-west-2_example

# Optional; defaults already allow local Vite dev/preview ports.
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```
