import Link from "next/link";

export default function AdminDashboardPage() {
  return (
    <div>
      <h1 className="text-2xl font-semibold">Dashboard</h1>
      <p className="mt-2 text-neutral-600">
        Use the sidebar to review drafts, manage published articles, and watch
        pipeline signals.
      </p>
      <ul className="mt-6 list-disc space-y-2 pl-6 text-neutral-700">
        <li>
          <Link href="/admin/drafts" className="text-blue-700 underline">
            Draft queue
          </Link>{" "}
          — story-draft artifacts from the pipeline
        </li>
        <li>
          <Link href="/admin/geos" className="text-blue-700 underline">
            CMS geos
          </Link>{" "}
          — map pipeline geos to reader subdomains
        </li>
      </ul>
    </div>
  );
}
