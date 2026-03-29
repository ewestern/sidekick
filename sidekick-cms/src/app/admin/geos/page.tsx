import { asc } from "drizzle-orm";

import { createCmsGeo, updateCmsGeo } from "@/app/admin/geos/actions";
import { db } from "@/db";
import { cmsGeos } from "@/db/schema";

export default async function AdminGeosPage() {
  const rows = await db.select().from(cmsGeos).orderBy(asc(cmsGeos.slug));

  return (
    <div>
      <h1 className="text-2xl font-semibold">CMS geos</h1>
      <p className="mt-1 text-sm text-neutral-600">
        Map pipeline geo codes to reader subdomains (e.g.{" "}
        <code>shasta.sidekick.news</code>).
      </p>

      <section className="mt-8 rounded-lg border border-neutral-200 bg-white p-6">
        <h2 className="text-lg font-medium">Add publication</h2>
        <form action={createCmsGeo} className="mt-4 space-y-3 max-w-xl">
          <label className="block text-sm">
            <span className="text-neutral-600">Subdomain slug</span>
            <input
              name="slug"
              required
              className="mt-1 w-full rounded border border-neutral-300 px-2 py-1"
              placeholder="shasta"
            />
          </label>
          <label className="block text-sm">
            <span className="text-neutral-600">Display name</span>
            <input
              name="name"
              required
              className="mt-1 w-full rounded border border-neutral-300 px-2 py-1"
              placeholder="Shasta County"
            />
          </label>
          <label className="block text-sm">
            <span className="text-neutral-600">Tagline (optional)</span>
            <input
              name="tagline"
              className="mt-1 w-full rounded border border-neutral-300 px-2 py-1"
            />
          </label>
          <label className="block text-sm">
            <span className="text-neutral-600">
              Pipeline geos (comma or newline separated)
            </span>
            <textarea
              name="pipeline_geos"
              rows={4}
              className="mt-1 w-full rounded border border-neutral-300 px-2 py-1 font-mono text-xs"
              placeholder="us:ca:shasta:shasta"
            />
          </label>
          <button
            type="submit"
            className="rounded bg-neutral-900 px-3 py-1.5 text-sm text-white"
          >
            Create
          </button>
        </form>
      </section>

      <section className="mt-10">
        <h2 className="text-lg font-medium">Existing</h2>
        <ul className="mt-4 space-y-6">
          {rows.map((g) => (
            <li
              key={g.id}
              className="rounded-lg border border-neutral-200 bg-white p-4"
            >
              <form action={updateCmsGeo} className="space-y-3 max-w-xl">
                <input type="hidden" name="id" value={g.id} />
                <label className="block text-sm">
                  <span className="text-neutral-600">Subdomain slug</span>
                  <input
                    name="slug"
                    defaultValue={g.slug}
                    required
                    className="mt-1 w-full rounded border border-neutral-300 px-2 py-1"
                  />
                </label>
                <label className="block text-sm">
                  <span className="text-neutral-600">Display name</span>
                  <input
                    name="name"
                    defaultValue={g.name}
                    required
                    className="mt-1 w-full rounded border border-neutral-300 px-2 py-1"
                  />
                </label>
                <label className="block text-sm">
                  <span className="text-neutral-600">Tagline</span>
                  <input
                    name="tagline"
                    defaultValue={g.tagline ?? ""}
                    className="mt-1 w-full rounded border border-neutral-300 px-2 py-1"
                  />
                </label>
                <label className="block text-sm">
                  <span className="text-neutral-600">Pipeline geos</span>
                  <textarea
                    name="pipeline_geos"
                    rows={3}
                    defaultValue={g.pipelineGeos.join("\n")}
                    className="mt-1 w-full rounded border border-neutral-300 px-2 py-1 font-mono text-xs"
                  />
                </label>
                <label className="block text-sm">
                  <span className="text-neutral-600">Status</span>
                  <select
                    name="status"
                    defaultValue={g.status}
                    className="mt-1 rounded border border-neutral-300 px-2 py-1"
                  >
                    <option value="active">active</option>
                    <option value="inactive">inactive</option>
                  </select>
                </label>
                <button
                  type="submit"
                  className="rounded border border-neutral-400 px-3 py-1.5 text-sm"
                >
                  Save
                </button>
              </form>
            </li>
          ))}
        </ul>
        {rows.length === 0 ? (
          <p className="mt-4 text-neutral-600">No CMS geos yet.</p>
        ) : null}
      </section>
    </div>
  );
}
