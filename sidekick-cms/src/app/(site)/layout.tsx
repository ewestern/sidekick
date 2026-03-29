import { headers } from "next/headers";
import Link from "next/link";

import { getCmsGeoBySlug } from "@/lib/cms-geo";

export default async function SiteLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const h = await headers();
  const slug =
    h.get("x-cms-geo-slug") ??
    process.env.DEFAULT_CMS_GEO_SLUG ??
    "local";
  const geo = await getCmsGeoBySlug(slug);

  if (!geo || geo.status !== "active") {
    return (
      <div className="mx-auto max-w-lg px-4 py-16 text-center">
        <h1 className="text-2xl font-semibold">Publication not found</h1>
        <p className="mt-2 text-neutral-600">
          No active CMS geo for slug <code>{slug}</code>. Seed{" "}
          <code>cms_geos</code> or set <code>DEFAULT_CMS_GEO_SLUG</code>.
        </p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-neutral-50 text-neutral-900">
      <header className="border-b border-neutral-200 bg-white">
        <div className="mx-auto flex max-w-3xl items-center justify-between gap-4 px-4 py-4">
          <div>
            <Link href="/" className="text-xl font-bold tracking-tight">
              {geo.name}
            </Link>
            {geo.tagline ? (
              <p className="text-sm text-neutral-600">{geo.tagline}</p>
            ) : null}
          </div>
          <nav className="flex gap-4 text-sm">
            <Link href="/" className="text-neutral-700 hover:underline">
              Home
            </Link>
            <Link href="/search" className="text-neutral-700 hover:underline">
              Search
            </Link>
            <Link href="/login" className="text-neutral-700 hover:underline">
              Sign in
            </Link>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-3xl px-4 py-8">{children}</main>
    </div>
  );
}
