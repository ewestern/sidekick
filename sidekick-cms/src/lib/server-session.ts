import { headers } from "next/headers";

import { auth } from "@/lib/auth";

export async function getServerSession() {
  return auth.api.getSession({ headers: await headers() });
}

export async function requireEditorSession() {
  const session = await getServerSession();
  if (!session) {
    return null;
  }
  const role = (session.user as { role?: string }).role ?? "subscriber";
  if (role !== "editor" && role !== "admin") {
    return null;
  }
  return session;
}
