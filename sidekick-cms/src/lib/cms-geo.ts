import { eq } from "drizzle-orm";

import { db } from "@/db";
import { cmsGeos } from "@/db/schema";

export async function getCmsGeoBySlug(slug: string) {
  const rows = await db
    .select()
    .from(cmsGeos)
    .where(eq(cmsGeos.slug, slug))
    .limit(1);
  return rows[0] ?? null;
}

export async function resolveCmsGeoForPipelineGeo(
  pipelineGeo: string | null,
): Promise<(typeof cmsGeos.$inferSelect) | null> {
  if (!pipelineGeo) {
    return null;
  }
  const active = await db
    .select()
    .from(cmsGeos)
    .where(eq(cmsGeos.status, "active"));
  return active.find((g) => g.pipelineGeos.includes(pipelineGeo)) ?? null;
}
