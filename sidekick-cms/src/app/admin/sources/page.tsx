import { listSources } from "@/lib/pipeline";

export default async function AdminSourcesPage() {
  let rows: Awaited<ReturnType<typeof listSources>> = [];
  try {
    rows = await listSources();
  } catch (e) {
    return (
      <div>
        <h1 className="text-2xl font-semibold">Sources</h1>
        <p className="mt-4 text-red-700">{(e as Error).message}</p>
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold">Source health</h1>
      <p className="mt-1 text-sm text-neutral-600">
        Read-only. Full CRUD lives in <code>admin/</code>.
      </p>
      <ul className="mt-6 space-y-3">
        {rows.map((s) => (
          <li
            key={s.id}
            className="rounded border border-neutral-200 bg-white p-3 text-sm"
          >
            <div className="font-medium">{s.name}</div>
            <div className="font-mono text-xs text-neutral-500">{s.id}</div>
            <pre className="mt-2 max-h-32 overflow-auto text-xs text-neutral-600">
              {JSON.stringify({ schedule: s.schedule, health: s.health }, null, 2)}
            </pre>
          </li>
        ))}
      </ul>
    </div>
  );
}
