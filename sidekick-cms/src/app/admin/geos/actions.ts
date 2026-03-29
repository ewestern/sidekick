"use server";

import { revalidatePath } from "next/cache";
import { eq } from "drizzle-orm";

import { db } from "@/db";
import { cmsGeos } from "@/db/schema";
import { requireEditorSession } from "@/lib/server-session";

function parsePipelineGeos(raw: string): string[] {
  return raw
    .split(/[\n,]+/)
    .map((s) => s.trim())
    .filter(Boolean);
}

export async function createCmsGeo(formData: FormData) {
  const session = await requireEditorSession();
  if (!session) {
    throw new Error("Unauthorized");
  }
  const slug = String(formData.get("slug") ?? "").trim();
  const name = String(formData.get("name") ?? "").trim();
  const pipelineGeosRaw = String(formData.get("pipeline_geos") ?? "");
  if (!slug || !name) {
    throw new Error("slug and name required");
  }
  const id = globalThis.crypto.randomUUID();
  const now = new Date();
  await db.insert(cmsGeos).values({
    id,
    slug,
    name,
    pipelineGeos: parsePipelineGeos(pipelineGeosRaw),
    status: "active",
    tagline: String(formData.get("tagline") ?? "").trim() || null,
    createdAt: now,
    updatedAt: now,
  });
  revalidatePath("/admin/geos");
}

export async function updateCmsGeo(formData: FormData) {
  const session = await requireEditorSession();
  if (!session) {
    throw new Error("Unauthorized");
  }
  const id = String(formData.get("id") ?? "");
  if (!id) {
    throw new Error("Missing id");
  }
  const now = new Date();
  await db
    .update(cmsGeos)
    .set({
      name: String(formData.get("name") ?? "").trim(),
      slug: String(formData.get("slug") ?? "").trim(),
      pipelineGeos: parsePipelineGeos(String(formData.get("pipeline_geos") ?? "")),
      status: String(formData.get("status") ?? "active"),
      tagline: String(formData.get("tagline") ?? "").trim() || null,
      updatedAt: now,
    })
    .where(eq(cmsGeos.id, id));
  revalidatePath("/admin/geos");
}
