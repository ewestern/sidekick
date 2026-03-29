import { headers } from "next/headers";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { and, eq } from "drizzle-orm";

import { db } from "@/db";
import { articles, cmsGeos } from "@/db/schema";

type Props = { params: Promise<{ slug: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug: articleSlug } = await params;
  const h = await headers();
  const geoSlug =
    h.get("x-cms-geo-slug") ??
    process.env.DEFAULT_CMS_GEO_SLUG ??
    "local";
  const [geo] = await db
    .select()
    .from(cmsGeos)
    .where(eq(cmsGeos.slug, geoSlug))
    .limit(1);
  if (!geo) {
    return { title: "Not found" };
  }
  const [row] = await db
    .select()
    .from(articles)
    .where(
      and(
        eq(articles.cmsGeoId, geo.id),
        eq(articles.slug, articleSlug),
      ),
    )
    .limit(1);
  if (!row) {
    return { title: "Not found" };
  }
  return {
    title: row.seoTitle ?? row.title,
    description: row.seoDescription ?? undefined,
  };
}

export default async function ArticlePage({ params }: Props) {
  const { slug: articleSlug } = await params;
  const h = await headers();
  const geoSlug =
    h.get("x-cms-geo-slug") ??
    process.env.DEFAULT_CMS_GEO_SLUG ??
    "local";
  const [geo] = await db
    .select()
    .from(cmsGeos)
    .where(eq(cmsGeos.slug, geoSlug))
    .limit(1);
  if (!geo) {
    notFound();
  }
  const [row] = await db
    .select()
    .from(articles)
    .where(
      and(
        eq(articles.cmsGeoId, geo.id),
        eq(articles.slug, articleSlug),
      ),
    )
    .limit(1);
  if (!row) {
    notFound();
  }

  return (
    <article>
      <h1 className="text-3xl font-bold tracking-tight">{row.title}</h1>
      <p className="mt-2 text-sm text-neutral-500">
        {row.publishedAt.toISOString().slice(0, 10)}
      </p>
      <div className="prose prose-neutral mt-8 max-w-none whitespace-pre-wrap">
        {row.bodyMarkdown}
      </div>
    </article>
  );
}
