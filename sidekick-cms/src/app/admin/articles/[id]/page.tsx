import { eq } from "drizzle-orm";
import { notFound } from "next/navigation";

import { updateArticle } from "@/app/admin/articles/[id]/actions";
import { db } from "@/db";
import { articles } from "@/db/schema";

type Props = { params: Promise<{ id: string }> };

export default async function EditArticlePage({ params }: Props) {
  const { id } = await params;
  const [row] = await db.select().from(articles).where(eq(articles.id, id)).limit(1);
  if (!row) {
    notFound();
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold">Edit article</h1>
      <form action={updateArticle} className="mt-6 max-w-3xl space-y-4">
        <input type="hidden" name="id" value={row.id} />
        <label className="block text-sm">
          <span className="text-neutral-600">Title</span>
          <input
            name="title"
            defaultValue={row.title}
            required
            className="mt-1 w-full rounded border border-neutral-300 px-2 py-1"
          />
        </label>
        <label className="block text-sm">
          <span className="text-neutral-600">Slug</span>
          <input
            name="slug"
            defaultValue={row.slug}
            required
            className="mt-1 w-full rounded border border-neutral-300 px-2 py-1 font-mono"
          />
        </label>
        <label className="block text-sm">
          <span className="text-neutral-600">Body (Markdown)</span>
          <textarea
            name="bodyMarkdown"
            rows={16}
            defaultValue={row.bodyMarkdown}
            className="mt-1 w-full rounded border border-neutral-300 px-2 py-1 font-mono text-sm"
          />
        </label>
        <label className="block text-sm">
          <span className="text-neutral-600">Visibility</span>
          <select
            name="visibility"
            defaultValue={row.visibility}
            className="mt-1 rounded border border-neutral-300 px-2 py-1"
          >
            <option value="public">public</option>
            <option value="members">members</option>
            <option value="paid">paid</option>
          </select>
        </label>
        <label className="block text-sm">
          <span className="text-neutral-600">SEO title</span>
          <input
            name="seoTitle"
            defaultValue={row.seoTitle ?? ""}
            className="mt-1 w-full rounded border border-neutral-300 px-2 py-1"
          />
        </label>
        <label className="block text-sm">
          <span className="text-neutral-600">SEO description</span>
          <textarea
            name="seoDescription"
            rows={2}
            defaultValue={row.seoDescription ?? ""}
            className="mt-1 w-full rounded border border-neutral-300 px-2 py-1"
          />
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            name="sendAsNewsletter"
            defaultChecked={row.sendAsNewsletter}
          />
          Send as newsletter (field only; delivery not implemented)
        </label>
        <p className="text-xs text-neutral-500">
          Source artifact:{" "}
          <code className="rounded bg-neutral-100 px-1">{row.sourceArtifactId}</code>
        </p>
        <button
          type="submit"
          className="rounded bg-neutral-900 px-3 py-1.5 text-sm text-white"
        >
          Save
        </button>
      </form>
    </div>
  );
}
