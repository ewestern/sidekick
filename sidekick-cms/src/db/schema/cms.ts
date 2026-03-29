/**
 * Sidekick CMS tables — hand-edited only. Never pass this file to better-auth generate.
 */
import { sql } from "drizzle-orm";
import {
  boolean,
  index,
  pgTable,
  text,
  timestamp,
  uniqueIndex,
} from "drizzle-orm/pg-core";

/** Reader-facing geography (subdomain publication). */
export const cmsGeos = pgTable("cms_geos", {
  id: text("id").primaryKey(),
  slug: text("slug").notNull().unique(),
  name: text("name").notNull(),
  pipelineGeos: text("pipeline_geos")
    .array()
    .notNull()
    .default(sql`'{}'::text[]`),
  status: text("status").notNull().default("active"),
  tagline: text("tagline"),
  timezone: text("timezone").default("America/Los_Angeles"),
  createdAt: timestamp("created_at", { mode: "date", withTimezone: true })
    .notNull()
    .$defaultFn(() => new Date()),
  updatedAt: timestamp("updated_at", { mode: "date", withTimezone: true })
    .notNull()
    .$defaultFn(() => new Date()),
});

/** Editorial state for story-draft artifacts (artifact IDs live in pipeline DB). */
export const draftReviews = pgTable("draft_reviews", {
  artifactId: text("artifact_id").primaryKey(),
  editorialStatus: text("editorial_status").notNull().default("pending"),
  reviewerId: text("reviewer_id"),
  feedbackNotes: text("feedback_notes"),
  chainRootId: text("chain_root_id"),
  createdAt: timestamp("created_at", { mode: "date", withTimezone: true })
    .notNull()
    .$defaultFn(() => new Date()),
  updatedAt: timestamp("updated_at", { mode: "date", withTimezone: true })
    .notNull()
    .$defaultFn(() => new Date()),
});

/** Published article (canonical reader record). */
export const articles = pgTable(
  "articles",
  {
    id: text("id").primaryKey(),
    sourceArtifactId: text("source_artifact_id").notNull(),
    cmsGeoId: text("cms_geo_id")
      .notNull()
      .references(() => cmsGeos.id, { onDelete: "restrict" }),
    slug: text("slug").notNull(),
    title: text("title").notNull(),
    bodyMarkdown: text("body_markdown").notNull().default(""),
    publishedAt: timestamp("published_at", { mode: "date", withTimezone: true }).notNull(),
    visibility: text("visibility").notNull().default("public"),
    seoTitle: text("seo_title"),
    seoDescription: text("seo_description"),
    sendAsNewsletter: boolean("send_as_newsletter").notNull().default(false),
    /** Nullable until pgvector enabled; store as text JSON array for portability or use real vector in prod */
    embeddingJson: text("embedding_json"),
    beat: text("beat"),
    searchVector: text("search_vector"),
    createdAt: timestamp("created_at", { mode: "date", withTimezone: true })
      .notNull()
      .$defaultFn(() => new Date()),
    updatedAt: timestamp("updated_at", { mode: "date", withTimezone: true })
      .notNull()
      .$defaultFn(() => new Date()),
  },
  (t) => [
    uniqueIndex("articles_cms_geo_slug_uidx").on(t.cmsGeoId, t.slug),
    uniqueIndex("articles_source_artifact_uidx").on(t.sourceArtifactId),
    index("articles_cms_geo_published_idx").on(t.cmsGeoId, t.publishedAt),
  ],
);
