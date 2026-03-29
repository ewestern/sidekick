import { headers } from "next/headers";
import Link from "next/link";
import { and, desc, eq, ilike, or } from "drizzle-orm";

import { db } from "@/db";
import { articles, cmsGeos } from "@/db/schema";

export default async function SearchPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string }>;
}) {
  const { q } = await searchParams;
  const h = await headers();
  const slug =
    h.get("x-cms-geo-slug") ??
    process.env.DEFAULT_CMS_GEO_SLUG ??
    "local";
  const [geo] = await db
    .select()
    .from(cmsGeos)
    .where(eq(cmsGeos.slug, slug))
    .limit(1);

  if (!geo) {
    return null;
  }

  const term = (q ?? "").trim();
  if (!term) {
    return (
      <div>
        <h1 className="text-2xl font-semibold">Search</h1>
        <p className="mt-2 text-neutral-600">
          Enter a query: <code>?q=...</code>
        </p>
      </div>
    );
  }

  const pattern = `%${term}%`;
  const rows = await db
    .select()
    .from(articles)
    .where(
      and(
        eq(articles.cmsGeoId, geo.id),
        or(
          ilike(articles.title, pattern),
          ilike(articles.bodyMarkdown, pattern),
        ),
      ),
    )
    .orderBy(desc(articles.publishedAt))
    .limit(50);

  return (
    <div>
      <h1 className="text-2xl font-semibold">Search: {term}</h1>
      <ul className="mt-6 space-y-4">
        {rows.map((a) => (
          <li key={a.id}>
            <Link href={`/${a.slug}`} className="font-medium hover:underline">
              {a.title}
            </Link>
          </li>
        ))}
      </ul>
      {rows.length === 0 ? (
        <p className="mt-4 text-neutral-600">No results.</p>
      ) : null}
    </div>
  );
}
