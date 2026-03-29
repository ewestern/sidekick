import { inArray } from "drizzle-orm";

import { DraftRow } from "@/app/admin/drafts/DraftRow";
import { db } from "@/db";
import { articles, draftReviews } from "@/db/schema";
import { listArtifacts } from "@/lib/pipeline";

export default async function AdminDraftsPage() {
  let pipelineDrafts: Awaited<ReturnType<typeof listArtifacts>> = [];
  try {
    pipelineDrafts = await listArtifacts({
      content_type: "story-draft",
      stage: "draft",
      status: "active",
    });
  } catch (e) {
    return (
      <div>
        <h1 className="text-2xl font-semibold">Drafts</h1>
        <p className="mt-4 rounded border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          Could not reach pipeline API. Set{" "}
          <code className="rounded bg-white px-1">PIPELINE_API_URL</code> and{" "}
          <code className="rounded bg-white px-1">PIPELINE_API_KEY</code>.
          <br />
          <span className="mt-2 block font-mono text-xs">
            {(e as Error).message}
          </span>
        </p>
      </div>
    );
  }

  const ids = pipelineDrafts.map((a) => a.id);
  const publishedRows =
    ids.length > 0
      ? await db
          .select({ sourceArtifactId: articles.sourceArtifactId })
          .from(articles)
          .where(inArray(articles.sourceArtifactId, ids))
      : [];
  const publishedSet = new Set(
    publishedRows.map((r) => r.sourceArtifactId),
  );

  const reviewRows =
    ids.length > 0
      ? await db
          .select()
          .from(draftReviews)
          .where(inArray(draftReviews.artifactId, ids))
      : [];
  const reviewById = new Map(reviewRows.map((r) => [r.artifactId, r]));

  const queue = pipelineDrafts.filter((a) => {
    if (publishedSet.has(a.id)) {
      return false;
    }
    const r = reviewById.get(a.id);
    if (!r) {
      return true;
    }
    return r.editorialStatus === "pending" || r.editorialStatus === "sent_back";
  });

  return (
    <div>
      <h1 className="text-2xl font-semibold">Draft queue</h1>
      <p className="mt-1 text-sm text-neutral-600">
        story-draft · stage=draft · active · not yet published
      </p>
      {queue.length === 0 ? (
        <p className="mt-6 text-neutral-600">No drafts in queue.</p>
      ) : (
        <ul className="mt-6 space-y-8">
          {queue.map((a) => (
            <li key={a.id}>
              <DraftRow artifact={a} review={reviewById.get(a.id) ?? null} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
