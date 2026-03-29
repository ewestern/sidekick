import { listAssignments } from "@/lib/pipeline";

export default async function AdminAssignmentsPage() {
  let data: unknown[] = [];
  try {
    data = await listAssignments();
  } catch (e) {
    return (
      <div>
        <h1 className="text-2xl font-semibold">Assignments</h1>
        <p className="mt-4 text-red-700">{(e as Error).message}</p>
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold">Assignments</h1>
      <p className="mt-1 text-sm text-neutral-600">
        Same data as <code>admin/</code> — editorial view. Create/update via API
        or admin app when needed.
      </p>
      <pre className="mt-6 max-h-[70vh] overflow-auto rounded border border-neutral-200 bg-white p-4 text-xs">
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  );
}
