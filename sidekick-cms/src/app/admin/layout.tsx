import Link from "next/link";
import { redirect } from "next/navigation";

import { requireEditorSession } from "@/lib/server-session";

const nav = [
  { href: "/admin", label: "Dashboard" },
  { href: "/admin/drafts", label: "Drafts" },
  { href: "/admin/articles", label: "Articles" },
  { href: "/admin/signals", label: "Signals" },
  { href: "/admin/assignments", label: "Assignments" },
  { href: "/admin/sources", label: "Sources" },
  { href: "/admin/geos", label: "CMS geos" },
  { href: "/admin/settings", label: "Settings" },
];

export default async function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await requireEditorSession();
  if (!session) {
    redirect("/login?next=/admin");
  }

  return (
    <div className="min-h-screen bg-neutral-100">
      <div className="flex min-h-screen">
        <aside className="w-52 shrink-0 border-r border-neutral-200 bg-white px-3 py-6">
          <p className="px-2 text-xs font-semibold uppercase tracking-wide text-neutral-500">
            Sidekick CMS
          </p>
          <nav className="mt-4 flex flex-col gap-1">
            {nav.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="rounded px-2 py-1.5 text-sm text-neutral-800 hover:bg-neutral-100"
              >
                {item.label}
              </Link>
            ))}
          </nav>
          <p className="mt-6 px-2 text-xs text-neutral-500">
            {session.user.email}
          </p>
        </aside>
        <div className="flex-1 overflow-auto p-8">{children}</div>
      </div>
    </div>
  );
}
