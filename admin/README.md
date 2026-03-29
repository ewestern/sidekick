# Sidekick Admin

Basic internal admin UI for managing Sidekick API core resources:

- sources
- assignments
- agent configs
- artifacts
- API clients (issue, rotate, revoke)

## Local development

From this `admin/` directory:

```bash
npm install
npm run sdk:generate
npm run dev
```

The SDK command expects the API service to expose OpenAPI at:

- `http://localhost:8080/openapi.json`

If your API is at a different URL, run:

```bash
npx openapi-ts -i "http://YOUR_API_HOST/openapi.json" -o src/client
```

## Cognito (Hosted UI)

The app uses `BrowserRouter` and path-based routes (`/callback`, `/logout`). Configure the Cognito app client with matching **Callback URL** and **Sign out URL** values.

Environment variables:

| Variable                 | Purpose                                                                                                  |
| ------------------------ | -------------------------------------------------------------------------------------------------------- |
| `VITE_COGNITO_DOMAIN`    | Hosted UI domain host, e.g. `your-prefix.auth.us-west-2.amazoncognito.com`                               |
| `VITE_COGNITO_CLIENT_ID` | Cognito app client ID                                                                                    |
| `VITE_REDIRECT_URI`      | OAuth redirect after login, e.g. `https://admin.example.com/callback`                                    |
| `VITE_LOGOUT_URI`        | URL passed to Cognito logout (`logout_uri`), typically the SPA origin, e.g. `https://admin.example.com/` |
| `VITE_API_URL`           | Sidekick API base URL                                                                                    |

**Production hosting:** the static host must serve `index.html` for client-side routes (`/`, `/callback`, `/logout`, `/sources`, …). Without that, direct loads or Cognito redirects to `/callback` will 404.

## Authentication and roles

The app supports two auth header modes:

- `Authorization: Bearer <jwt>`
- `X-API-Key: <key>`

Role requirements (from API auth model):

- `reader`: read endpoints
- `editor`: write for sources/assignments and artifact patch
- `admin`: agent configs write/delete and machine key management

For API clients operations (issue/rotate/revoke), use `admin` credentials.
