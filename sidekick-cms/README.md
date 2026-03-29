# sidekick-cms

Next.js App Router app: **editorial admin** (`/admin/*`), **public reader site** (same app, Server Components read the CMS DB via Drizzle), and **better-auth** (email/password; magic link can be added via plugin).

Pipeline integration goes through **FastAPI** (`PIPELINE_API_URL` + `PIPELINE_API_KEY`); published articles are read from this app’s Postgres only (no extra HTTP hop for SSR pages).

## Prerequisites

- Node 20+
- Postgres 16+ (pgvector not required for v1; `embedding_json` is optional)
- Running Sidekick API for drafts/signals/sources/assignments

## Setup

```bash
cp .env.example .env.local
# Create DB and apply migrations
createdb sidekick_cms   # or your cloud instance
npm install
npm run db:migrate      # applies drizzle/*.sql
npm run dev
```

### First-time content

1. **CMS geo** — In `/admin/geos`, create a row whose `slug` matches how you reach the site (e.g. `local` when using `DEFAULT_CMS_GEO_SLUG=local` on plain `localhost`, or `shasta` for `shasta.localhost:3000`).
2. **Pipeline geo mapping** — Set `pipeline_geos` to the pipeline codes that map to that publication (many pipeline geos → one CMS geo).
3. **Editor user** — Sign up at `/signup`, then promote in SQL:

```sql
UPDATE "user" SET role = 'editor' WHERE email = 'you@example.com';
```

(`admin` is also allowed for `/admin/*`.)

## Database schema layout

- **`src/db/schema/auth.ts`** — better-auth tables only. This is the **only** file you should pass to `better-auth generate --output …` when you add or upgrade plugins. After regenerating, re-add hand columns on `user` if the CLI removed them (`role`, `emailSubscribed`), then run `npm run db:generate` for any new tables/columns.
- **`src/db/schema/cms.ts`** — CMS tables (`cms_geos`, `draft_reviews`, `articles`). Never overwrite with the auth CLI.
- **`src/db/schema/index.ts`** — re-exports both for Drizzle Kit and `import { … } from "@/db/schema"`.

## Scripts

| Command          | Purpose                |
| ---------------- | ---------------------- |
| `npm run dev`    | Next dev server        |
| `npm run build`  | Production build       |
| `npm run db:migrate` | Apply Drizzle migrations |
| `npm run db:push`    | Push schema (dev only)   |
| `npm run db:studio`  | Drizzle Studio           |

## Routing

- **Middleware** sets `x-cms-geo-slug` from the request host (`shasta.sidekick.news` → `shasta`, `shasta.localhost` → `shasta`). Admin, API, login, and signup paths skip geo injection.
- **Public** home and articles are scoped to the resolved CMS geo.
- **Beats** are never shown on public routes; they remain internal on admin drafts/signals.

## API changes (repo)

`GET /artifacts` accepts optional query params: `content_type`, repeated `content_types`, `stage`, `status`.

## Not wired yet

- **Send-back → editor agent**: `sendBackDraft` only updates `draft_reviews` in the CMS DB. Calling the pipeline to re-run the editor agent should be added (FastAPI route or Step Functions), per product plan.
- **Magic link / passkeys / Stripe**: better-auth plugins can be enabled when you are ready.
- **Full-text `tsvector`**: search uses `ILIKE` on title and body for v1.
