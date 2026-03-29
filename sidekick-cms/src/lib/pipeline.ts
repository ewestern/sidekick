const pipelineBase =
  process.env.PIPELINE_API_URL?.replace(/\/$/, "") ?? "http://127.0.0.1:8080";

export type PipelineArtifact = {
  id: string;
  title: string;
  content_type: string;
  stage: string;
  beat: string | null;
  geo: string | null;
  status: string;
  assignment_id: string | null;
  content_uri: string | null;
  created_at: string;
};

async function pipelineFetch(
  path: string,
  init?: RequestInit,
): Promise<Response> {
  const key = process.env.PIPELINE_API_KEY;
  const headers = new Headers(init?.headers);
  headers.set("Accept", "application/json");
  if (key) {
    headers.set("X-API-Key", key);
  }
  return fetch(`${pipelineBase}${path}`, {
    ...init,
    headers,
    cache: "no-store",
  });
}

export async function listArtifacts(params: {
  content_type?: string;
  content_types?: string[];
  stage?: string;
  status?: string;
}): Promise<PipelineArtifact[]> {
  const search = new URLSearchParams();
  if (params.content_type) {
    search.set("content_type", params.content_type);
  }
  if (params.content_types?.length) {
    for (const ct of params.content_types) {
      search.append("content_types", ct);
    }
  }
  if (params.stage) {
    search.set("stage", params.stage);
  }
  if (params.status) {
    search.set("status", params.status);
  }
  const q = search.toString();
  const path = q ? `/artifacts?${q}` : "/artifacts";
  const res = await pipelineFetch(path);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Pipeline API ${res.status}: ${text}`);
  }
  return (await res.json()) as PipelineArtifact[];
}

export async function getArtifact(id: string): Promise<PipelineArtifact> {
  const res = await pipelineFetch(`/artifacts/${encodeURIComponent(id)}`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Pipeline API ${res.status}: ${text}`);
  }
  return (await res.json()) as PipelineArtifact;
}

export async function listSources(): Promise<
  { id: string; name: string; health: unknown; schedule: unknown }[]
> {
  const res = await pipelineFetch("/sources");
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Pipeline API ${res.status}: ${text}`);
  }
  return (await res.json()) as { id: string; name: string; health: unknown; schedule: unknown }[];
}

export async function listAssignments(): Promise<unknown[]> {
  const res = await pipelineFetch("/assignments");
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Pipeline API ${res.status}: ${text}`);
  }
  return (await res.json()) as unknown[];
}
