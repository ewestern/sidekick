import {
  approveDraft,
  rejectDraft,
  sendBackDraft,
} from "@/app/admin/drafts/actions";

type Artifact = {
  id: string;
  title: string;
  beat: string | null;
  geo: string | null;
  created_at: string;
};

type Review = {
  editorialStatus: string;
  feedbackNotes: string | null;
} | null;

export function DraftRow({
  artifact,
  review,
}: {
  artifact: Artifact;
  review: Review;
}) {
  return (
    <div className="rounded-lg border border-neutral-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h2 className="text-lg font-medium">{artifact.title}</h2>
          <p className="mt-1 font-mono text-xs text-neutral-500">{artifact.id}</p>
          <p className="mt-1 text-sm text-neutral-600">
            beat: {artifact.beat ?? "—"} · pipeline geo: {artifact.geo ?? "—"}
          </p>
          {review?.editorialStatus === "sent_back" && review.feedbackNotes ? (
            <p className="mt-2 rounded bg-amber-50 p-2 text-sm text-amber-900">
              <strong>Sent back:</strong> {review.feedbackNotes}
            </p>
          ) : null}
        </div>
        <span className="rounded bg-neutral-100 px-2 py-0.5 text-xs text-neutral-700">
          {review?.editorialStatus ?? "pending"}
        </span>
      </div>

      <form action={approveDraft} className="mt-4 space-y-2 border-t border-neutral-100 pt-4">
        <input type="hidden" name="artifactId" value={artifact.id} />
        <label className="block text-sm">
          <span className="text-neutral-600">Slug (optional)</span>
          <input
            name="slug"
            type="text"
            className="mt-1 w-full max-w-md rounded border border-neutral-300 px-2 py-1 font-mono text-sm"
            placeholder="auto from title"
          />
        </label>
        <label className="block text-sm">
          <span className="text-neutral-600">Body (Markdown)</span>
          <textarea
            name="bodyMarkdown"
            rows={8}
            className="mt-1 w-full rounded border border-neutral-300 px-2 py-1 font-mono text-sm"
            defaultValue={
              "# Draft\n\nEdit before publish. Sync from artifact store can be wired later."
            }
          />
        </label>
        <button
          type="submit"
          className="rounded bg-emerald-700 px-3 py-1.5 text-sm text-white hover:bg-emerald-800"
        >
          Approve & publish
        </button>
      </form>

      <div className="mt-4 flex flex-wrap gap-4 border-t border-neutral-100 pt-4">
        <form action={sendBackDraft} className="flex flex-1 flex-col gap-2">
          <input type="hidden" name="artifactId" value={artifact.id} />
          <textarea
            name="notes"
            required
            rows={2}
            placeholder="Feedback for editor agent…"
            className="w-full rounded border border-neutral-300 px-2 py-1 text-sm"
          />
          <button
            type="submit"
            className="self-start rounded border border-amber-600 px-3 py-1.5 text-sm text-amber-900 hover:bg-amber-50"
          >
            Send back
          </button>
        </form>
        <form action={rejectDraft}>
          <input type="hidden" name="artifactId" value={artifact.id} />
          <input type="hidden" name="notes" value="" />
          <button
            type="submit"
            className="rounded border border-red-300 px-3 py-1.5 text-sm text-red-800 hover:bg-red-50"
          >
            Reject
          </button>
        </form>
      </div>
    </div>
  );
}
