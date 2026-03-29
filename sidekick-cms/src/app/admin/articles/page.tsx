import Link from "next/link";
import { desc, eq } from "drizzle-orm";

import { db } from "@/db";
import { articles, cmsGeos } from "@/db/schema";

export default async function AdminArticlesPage() {
  const rows = await db
    .select({
      article: articles,
      geoSlug: cmsGeos.slug,
      geoName: cmsGeos.name,
    })
    .from(articles)
    .innerJoin(cmsGeos, eq(articles.cmsGeoId, cmsGeos.id))
    .orderBy(desc(articles.publishedAt));

  return (
    <div>
      <h1 className="text-2xl font-semibold">Published articles</h1>
      <p className="mt-1 text-sm text-neutral-600">
        Canonical CMS records. Public site reads these via Drizzle (no API hop).
      </p>
      {rows.length === 0 ? (
        <p className="mt-6 text-neutral-600">No articles yet.</p>
      ) : (
        <table className="mt-6 w-full border-collapse text-sm">
          <thead>
            <tr className="border-b text-left text-neutral-600">
              <th className="py-2 pr-4">Title</th>
              <th className="py-2 pr-4">Geo</th>
              <th className="py-2 pr-4">Slug</th>
              <th className="py-2 pr-4">Visibility</th>
              <th className="py-2 pr-4">Published</th>
              <th className="py-2">Beat (internal)</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(({ article: a, geoSlug }) => (
              <tr key={a.id} className="border-b border-neutral-100">
                <td className="py-2 pr-4">
                  <Link
                    href={`/admin/articles/${a.id}`}
                    className="font-medium text-blue-700 hover:underline"
                  >
                    {a.title}
                  </Link>
                </td>
                <td className="py-2 pr-4 font-mono text-xs">{geoSlug}</td>
                <td className="py-2 pr-4 font-mono text-xs">{a.slug}</td>
                <td className="py-2 pr-4">{a.visibility}</td>
                <td className="py-2 pr-4 text-neutral-600">
                  {a.publishedAt.toISOString().slice(0, 10)}
                </td>
                <td className="py-2 font-mono text-xs text-neutral-500">
                  {a.beat ?? "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
