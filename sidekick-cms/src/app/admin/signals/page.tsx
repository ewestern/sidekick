import { listArtifacts } from "@/lib/pipeline";

const SIGNAL_TYPES = [
  "beat-brief",
  "flag",
  "trend-note",
  "connection-memo",
  "cross-beat-flag",
];

export default async function AdminSignalsPage() {
  let rows: Awaited<ReturnType<typeof listArtifacts>> = [];
  try {
    rows = await listArtifacts({
      content_types: SIGNAL_TYPES,
      status: "active",
    });
  } catch (e) {
    return (
      <div>
        <h1 className="text-2xl font-semibold">Editorial signals</h1>
        <p className="mt-4 text-red-700">{(e as Error).message}</p>
      </div>
    );
  }

  rows.sort(
    (a, b) =>
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  );

  return (
    <div>
      <h1 className="text-2xl font-semibold">Editorial signals</h1>
      <p className="mt-1 text-sm text-neutral-600">
        Analysis artifacts (latest first). Beat labels are editorial context only.
      </p>
      {rows.length === 0 ? (
        <p className="mt-6 text-neutral-600">No signal artifacts found.</p>
      ) : (
        <ul className="mt-6 space-y-3">
          {rows.map((a) => (
            <li
              key={a.id}
              className="rounded border border-neutral-200 bg-white p-3 text-sm"
            >
              <span className="font-mono text-xs text-neutral-500">{a.id}</span>
              <div className="mt-1 font-medium">{a.title}</div>
              <div className="mt-1 text-neutral-600">
                <code>{a.content_type}</code>
                {a.beat ? (
                  <>
                    {" "}
                    · beat <code>{a.beat}</code>
                  </>
                ) : null}
                {a.geo ? (
                  <>
                    {" "}
                    · geo <code>{a.geo}</code>
                  </>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
