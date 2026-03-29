import Link from "next/link";

export default function AdminSettingsPage() {
  return (
    <div>
      <h1 className="text-2xl font-semibold">Site configuration</h1>
      <p className="mt-2 text-neutral-600">
        Per-geo name, tagline, and timezone live on{" "}
        <Link href="/admin/geos" className="text-blue-700 underline">
          CMS geos
        </Link>
        . Global env: <code>BETTER_AUTH_URL</code>,{" "}
        <code>PIPELINE_API_URL</code>, <code>DEFAULT_CMS_GEO_SLUG</code>.
      </p>
    </div>
  );
}
