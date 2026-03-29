"use server";

import { revalidatePath } from "next/cache";
import { eq } from "drizzle-orm";

import { db } from "@/db";
import { articles, cmsGeos } from "@/db/schema";
import { requireEditorSession } from "@/lib/server-session";

export async function updateArticle(formData: FormData) {
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
    .update(articles)
    .set({
      title: String(formData.get("title") ?? "").trim(),
      slug: String(formData.get("slug") ?? "").trim(),
      bodyMarkdown: String(formData.get("bodyMarkdown") ?? ""),
      visibility: String(formData.get("visibility") ?? "public"),
      seoTitle: String(formData.get("seoTitle") ?? "").trim() || null,
      seoDescription: String(formData.get("seoDescription") ?? "").trim() || null,
      sendAsNewsletter: String(formData.get("sendAsNewsletter") ?? "") === "on",
      updatedAt: now,
    })
    .where(eq(articles.id, id));

  const [row] = await db
    .select({ slug: articles.slug, geoSlug: cmsGeos.slug })
    .from(articles)
    .innerJoin(cmsGeos, eq(articles.cmsGeoId, cmsGeos.id))
    .where(eq(articles.id, id))
    .limit(1);

  revalidatePath("/admin/articles");
  revalidatePath("/");
  if (row) {
    revalidatePath(`/${row.slug}`);
  }
}
