# sidekick-cms

> **Status**: draft (implementation in progress)  
> **Scope**: Next.js app at repo root `sidekick-cms/` — editorial UI, CMS tables, public SSR reader pages, better-auth; pipeline bridge via FastAPI only.  
> **Last updated**: 2026-03-29

## Decision log

| Date       | Decision | Rationale |
| ---------- | -------- | --------- |
| 2026-03-29 | Ship `sidekick-cms` as Next.js + Drizzle + better-auth | Matches feature plan: shared app for admin + reader SSR (no API hop for article reads). |
| 2026-03-29 | CMS tables in separate Postgres (`CMS_DATABASE_URL`) | Isolated from pipeline `models.py` / Alembic. |
| 2026-03-29 | `GET /artifacts` query filters + `content_types` | Lets CMS fetch story-drafts and signal types without loading the full artifact table. |

Operational details: [sidekick-cms/README.md](../sidekick-cms/README.md).
