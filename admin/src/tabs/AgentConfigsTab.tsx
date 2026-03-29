import { useEffect } from "react";
import type { AgentConfig } from "../client/types.gen";
import { api } from "../lib/api";
import { useResource } from "../hooks/useResource";
import { useFilter } from "../hooks/useFilter";
import { useForm } from "../hooks/useForm";
import { useConfirm } from "../components/ui/ConfirmDialog";
import { DataTable, type Column } from "../components/ui/DataTable";
import { SearchInput } from "../components/ui/SearchInput";
import {
  JsonField,
  TagField,
  TextField,
} from "../components/ui/FieldRenderers";

type FormValues = {
  agent_id: string;
  model: string;
  skills: string;
  prompts_text: string;
};

const DEFAULTS: FormValues = {
  agent_id: "",
  model: "claude-sonnet-4-6",
  skills: "",
  prompts_text: JSON.stringify({ system: "" }, null, 2),
};

function parsePrompts(text: string): Record<string, string> {
  try {
    const parsed = JSON.parse(text) as Record<string, unknown>;
    return Object.fromEntries(
      Object.entries(parsed).filter(([, v]) => typeof v === "string"),
    ) as Record<string, string>;
  } catch {
    return {};
  }
}

function parseSkills(value: string): string[] {
  return value
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

const COLUMNS: Column<AgentConfig>[] = [
  { key: "agent_id", label: "Agent ID", render: (row) => row.agent_id },
  { key: "model", label: "Model", render: (row) => row.model },
  {
    key: "skills",
    label: "Skills",
    render: (row) => String((row.skills ?? []).length),
  },
  {
    key: "updated_at",
    label: "Updated",
    render: (row) =>
      row.updated_at ? new Date(row.updated_at).toLocaleDateString() : "—",
  },
];

const SEARCH_FIELDS: (keyof AgentConfig)[] = ["agent_id", "model"];

export function AgentConfigsTab() {
  const resource = useResource<AgentConfig>({
    list: api.listAgentConfigs,
    getId: (c) => c.agent_id,
  });

  const { query, setQuery, filtered } = useFilter(resource.rows, SEARCH_FIELDS);
  const form = useForm<FormValues>(DEFAULTS);
  const { confirm, dialog } = useConfirm();

  const isEditing = resource.selected !== null;

  useEffect(() => {
    if (resource.selected) {
      form.setAll({
        agent_id: resource.selected.agent_id,
        model: resource.selected.model,
        skills: (resource.selected.skills ?? []).join(", "),
        prompts_text: JSON.stringify(resource.selected.prompts, null, 2),
      });
    } else {
      form.reset();
    }
  }, [resource.selected]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSelect = (row: AgentConfig) => {
    resource.select(resource.selected?.agent_id === row.agent_id ? null : row);
  };

  const buildPayload = () => ({
    agent_id: form.values.agent_id,
    model: form.values.model,
    prompts: parsePrompts(form.values.prompts_text),
    skills: parseSkills(form.values.skills),
  });

  const handleCreate = () => {
    void resource.exec(() => api.createAgentConfig(buildPayload()), {
      successMsg: "Agent config created",
    });
  };

  const handleUpsert = () => {
    void resource.exec(
      () => api.putAgentConfig(form.values.agent_id, buildPayload()),
      {
        successMsg: "Agent config saved",
      },
    );
  };

  const handleDelete = async () => {
    const ok = await confirm({
      title: "Delete agent config",
      message: `Delete config for "${resource.selected?.agent_id}"?`,
      confirmLabel: "Delete",
      variant: "danger",
    });
    if (!ok) return;
    const deleted = await resource.exec(
      () => api.deleteAgentConfig(resource.selected!.agent_id),
      {
        successMsg: "Agent config deleted",
      },
    );
    if (deleted) resource.select(null);
  };

  return (
    <div className="tab-page">
      {dialog}

      <div className="tab-header">
        <h2>Agent Configs</h2>
        {resource.loading && <span className="loading-text">Loading…</span>}
        {resource.listError && (
          <span className="error">{resource.listError}</span>
        )}
      </div>

      <div className="master-detail">
        {/* List pane */}
        <div className="list-pane">
          <div className="list-pane-header">
            <SearchInput
              value={query}
              onChange={setQuery}
              placeholder="Filter configs…"
            />
          </div>
          <div className="list-pane-body">
            <DataTable
              columns={COLUMNS}
              rows={filtered}
              selectedId={resource.selected?.agent_id ?? null}
              getId={(c) => c.agent_id}
              onSelect={handleSelect}
              emptyMessage="No agent configs yet."
            />
          </div>
        </div>

        {/* Detail pane */}
        <div className="detail-pane">
          <div className="detail-pane-header">
            <h3>{isEditing ? "Edit config" : "New config"}</h3>
            {isEditing && (
              <button
                className="secondary"
                onClick={() => resource.select(null)}
              >
                + New
              </button>
            )}
          </div>

          <div className="detail-pane-body">
            <TextField
              label="Agent ID"
              value={form.values.agent_id}
              onChange={(v) => form.set("agent_id", v)}
              placeholder="beat-agent:government:city-council"
              readOnly={isEditing}
            />
            <TextField
              label="Model"
              value={form.values.model}
              onChange={(v) => form.set("model", v)}
              placeholder="claude-sonnet-4-6"
            />
            <TagField
              label="Skills (comma-separated)"
              value={form.values.skills}
              onChange={(v) => form.set("skills", v)}
              placeholder="news-values, entity-and-actor-tracking"
            />
            <JsonField
              label="Prompts JSON"
              value={form.values.prompts_text}
              onChange={(v) => form.set("prompts_text", v)}
              rows={10}
            />
          </div>

          <div className="detail-pane-actions">
            {isEditing ? (
              <>
                <button
                  className="primary"
                  onClick={handleUpsert}
                  disabled={resource.loading}
                >
                  Save (upsert)
                </button>
                <button
                  className="danger"
                  onClick={() => void handleDelete()}
                  disabled={resource.loading}
                >
                  Delete
                </button>
              </>
            ) : (
              <>
                <button
                  className="primary"
                  onClick={handleCreate}
                  disabled={resource.loading}
                >
                  Create
                </button>
                <button onClick={handleUpsert} disabled={resource.loading}>
                  Upsert
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
