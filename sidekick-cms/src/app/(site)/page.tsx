import { headers } from "next/headers";
import Link from "next/link";
import { desc, eq } from "drizzle-orm";

import { db } from "@/db";
import { articles, cmsGeos } from "@/db/schema";

export default async function HomePage() {
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

  const rows = await db
    .select()
    .from(articles)
    .where(eq(articles.cmsGeoId, geo.id))
    .orderBy(desc(articles.publishedAt))
    .limit(50);

  if (rows.length === 0) {
    return (
      <p className="text-neutral-600">
        No published articles yet for this publication.
      </p>
    );
  }

  return (
    <ul className="space-y-6">
      {rows.map((a) => (
        <li key={a.id} className="border-b border-neutral-200 pb-6">
          <Link href={`/${a.slug}`} className="text-lg font-semibold hover:underline">
            {a.title}
          </Link>
          <p className="text-sm text-neutral-500">
            {a.publishedAt.toISOString().slice(0, 10)}
          </p>
        </li>
      ))}
    </ul>
  );
}
