"use server";

import { revalidatePath } from "next/cache";
import { eq } from "drizzle-orm";

import { db } from "@/db";
import { articles, draftReviews } from "@/db/schema";
import { resolveCmsGeoForPipelineGeo } from "@/lib/cms-geo";
import { getArtifact } from "@/lib/pipeline";
import { requireEditorSession } from "@/lib/server-session";
import { slugify } from "@/lib/slug";

async function upsertDraftReview(
  artifactId: string,
  status: string,
  reviewerId: string,
  feedbackNotes?: string | null,
  chainRootId?: string | null,
) {
  const now = new Date();
  await db
    .insert(draftReviews)
    .values({
      artifactId,
      editorialStatus: status,
      reviewerId,
      feedbackNotes: feedbackNotes ?? null,
      chainRootId: chainRootId ?? artifactId,
      createdAt: now,
      updatedAt: now,
    })
    .onConflictDoUpdate({
      target: draftReviews.artifactId,
      set: {
        editorialStatus: status,
        reviewerId,
        feedbackNotes: feedbackNotes ?? null,
        chainRootId: chainRootId ?? artifactId,
        updatedAt: now,
      },
    });
}

export async function approveDraft(formData: FormData) {
  const session = await requireEditorSession();
  if (!session) {
    throw new Error("Unauthorized");
  }
  const artifactId = String(formData.get("artifactId") ?? "");
  if (!artifactId) {
    throw new Error("Missing artifactId");
  }
  const customSlug = String(formData.get("slug") ?? "").trim();
  const bodyMarkdown = String(formData.get("bodyMarkdown") ?? "");

  const artifact = await getArtifact(artifactId);
  const cmsGeo = await resolveCmsGeoForPipelineGeo(artifact.geo);
  if (!cmsGeo) {
    throw new Error(
      `No CMS geo maps pipeline geo "${artifact.geo ?? ""}". Configure cms_geos.pipeline_geos.`,
    );
  }

  const existing = await db
    .select({ id: articles.id })
    .from(articles)
    .where(eq(articles.sourceArtifactId, artifactId))
    .limit(1);
  if (existing.length > 0) {
    throw new Error("This draft is already published.");
  }

  const slug = customSlug || slugify(artifact.title);
  const id = globalThis.crypto.randomUUID();
  const now = new Date();

  await db.transaction(async (tx) => {
    await tx.insert(articles).values({
      id,
      sourceArtifactId: artifactId,
      cmsGeoId: cmsGeo.id,
      slug,
      title: artifact.title,
      bodyMarkdown,
      publishedAt: now,
      visibility: "public",
      seoTitle: artifact.title,
      beat: artifact.beat,
    });
    await tx
      .insert(draftReviews)
      .values({
        artifactId,
        editorialStatus: "approved",
        reviewerId: session.user.id,
        chainRootId: artifactId,
        createdAt: now,
        updatedAt: now,
      })
      .onConflictDoUpdate({
        target: draftReviews.artifactId,
        set: {
          editorialStatus: "approved",
          reviewerId: session.user.id,
          updatedAt: now,
        },
      });
  });

  revalidatePath("/");
  revalidatePath(`/${slug}`);
  revalidatePath("/admin/articles");
  revalidatePath("/admin/drafts");
}

export async function rejectDraft(formData: FormData) {
  const session = await requireEditorSession();
  if (!session) {
    throw new Error("Unauthorized");
  }
  const artifactId = String(formData.get("artifactId") ?? "");
  if (!artifactId) {
    throw new Error("Missing artifactId");
  }
  await upsertDraftReview(
    artifactId,
    "rejected",
    session.user.id,
    String(formData.get("notes") ?? "") || null,
  );
  revalidatePath("/admin/drafts");
}

export async function sendBackDraft(formData: FormData) {
  const session = await requireEditorSession();
  if (!session) {
    throw new Error("Unauthorized");
  }
  const artifactId = String(formData.get("artifactId") ?? "");
  const notes = String(formData.get("notes") ?? "");
  if (!artifactId) {
    throw new Error("Missing artifactId");
  }
  if (!notes.trim()) {
    throw new Error("Feedback notes required for send-back");
  }
  await upsertDraftReview(
    artifactId,
    "sent_back",
    session.user.id,
    notes,
    artifactId,
  );
  revalidatePath("/admin/drafts");
}
