import {
  createAgentConfigAgentConfigsPost,
  createApiClientApiClientsPost,
  createAssignmentAssignmentsPost,
  createSourceSourcesPost,
  deleteAgentConfigAgentConfigsAgentIdDelete,
  deleteAssignmentAssignmentsAssignmentIdDelete,
  deleteSourceSourcesSourceIdDelete,
  getAgentConfigAgentConfigsAgentIdGet,
  getArtifactArtifactsArtifactIdGet,
  getAssignmentAssignmentsAssignmentIdGet,
  getSourceSourcesSourceIdGet,
  listAgentConfigsAgentConfigsGet,
  listApiClientsApiClientsGet,
  listArtifactsArtifactsGet,
  listAssignmentsAssignmentsGet,
  listSourcesSourcesGet,
  patchArtifactArtifactsArtifactIdPatch,
  patchAssignmentAssignmentsAssignmentIdPatch,
  patchSourceSourcesSourceIdPatch,
  putAgentConfigAgentConfigsAgentIdPut,
  retractArtifactArtifactsArtifactIdDelete,
  revokeApiClientApiClientsClientIdRevokePost,
  rotateApiClientKeyApiClientsClientIdRotatePost,
} from "../client/sdk.gen";
import { client } from "../client/client.gen";
import type {
  AgentConfigCreate,
  ApiClientCreate,
  ApiClientRotate,
  ArtifactPatch,
  AssignmentCreate,
  AssignmentPatch,
  SourceCreate,
  SourcePatch,
} from "../client/types.gen";
import { getIdToken, login } from "./auth";

const apiBaseUrl =
  import.meta.env.VITE_API_URL?.trim() || "http://localhost:8080";

export function configureApi(): void {
  const token = getIdToken();
  client.setConfig({
    baseUrl: apiBaseUrl,
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    responseStyle: "data",
    throwOnError: true,
    fetch: async (input, init) => {
      const response = await window.fetch(input, init);
      if (response.status === 401 && window.location.pathname !== "/callback") {
        void login();
      }
      return response;
    },
  });
}

export function parseApiError(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  return "Request failed";
}

export const api = {
  listSources: () => listSourcesSourcesGet(),
  getSource: (sourceId: string) =>
    getSourceSourcesSourceIdGet({ path: { source_id: sourceId } }),
  createSource: (body: SourceCreate) => createSourceSourcesPost({ body }),
  patchSource: (sourceId: string, body: SourcePatch) =>
    patchSourceSourcesSourceIdPatch({ path: { source_id: sourceId }, body }),
  deleteSource: (sourceId: string) =>
    deleteSourceSourcesSourceIdDelete({ path: { source_id: sourceId } }),

  listAssignments: () => listAssignmentsAssignmentsGet(),
  getAssignment: (assignmentId: string) =>
    getAssignmentAssignmentsAssignmentIdGet({
      path: { assignment_id: assignmentId },
    }),
  createAssignment: (body: AssignmentCreate) =>
    createAssignmentAssignmentsPost({ body }),
  patchAssignment: (assignmentId: string, body: AssignmentPatch) =>
    patchAssignmentAssignmentsAssignmentIdPatch({
      path: { assignment_id: assignmentId },
      body,
    }),
  deleteAssignment: (assignmentId: string) =>
    deleteAssignmentAssignmentsAssignmentIdDelete({
      path: { assignment_id: assignmentId },
    }),

  listAgentConfigs: () => listAgentConfigsAgentConfigsGet(),
  getAgentConfig: (agentId: string) =>
    getAgentConfigAgentConfigsAgentIdGet({ path: { agent_id: agentId } }),
  createAgentConfig: (body: AgentConfigCreate) =>
    createAgentConfigAgentConfigsPost({ body }),
  putAgentConfig: (agentId: string, body: AgentConfigCreate) =>
    putAgentConfigAgentConfigsAgentIdPut({ path: { agent_id: agentId }, body }),
  deleteAgentConfig: (agentId: string) =>
    deleteAgentConfigAgentConfigsAgentIdDelete({ path: { agent_id: agentId } }),

  listArtifacts: () => listArtifactsArtifactsGet(),
  getArtifact: (artifactId: string) =>
    getArtifactArtifactsArtifactIdGet({ path: { artifact_id: artifactId } }),
  patchArtifact: (artifactId: string, body: ArtifactPatch) =>
    patchArtifactArtifactsArtifactIdPatch({
      path: { artifact_id: artifactId },
      body,
    }),
  retractArtifact: (artifactId: string) =>
    retractArtifactArtifactsArtifactIdDelete({
      path: { artifact_id: artifactId },
    }),

  listApiClients: () => listApiClientsApiClientsGet(),
  createApiClient: (body: ApiClientCreate) =>
    createApiClientApiClientsPost({ body }),
  rotateApiClient: (clientId: string, body: ApiClientRotate) =>
    rotateApiClientKeyApiClientsClientIdRotatePost({
      path: { client_id: clientId },
      body,
    }),
  revokeApiClient: (clientId: string) =>
    revokeApiClientApiClientsClientIdRevokePost({
      path: { client_id: clientId },
    }),
};
