import { useState, useEffect } from "react";
import type { Artifact } from "../client/types.gen";
import { api } from "../lib/api";
import { useResource } from "../hooks/useResource";
import { useFilter } from "../hooks/useFilter";
import { useForm } from "../hooks/useForm";
import { useConfirm } from "../components/ui/ConfirmDialog";
import { DataTable, type Column } from "../components/ui/DataTable";
import { SearchInput } from "../components/ui/SearchInput";
import { StatusBadge } from "../components/ui/StatusBadge";
import {
  ReadOnlyField,
  SelectField,
  TagField,
  TextField,
} from "../components/ui/FieldRenderers";

type PatchValues = {
  status: string;
  beat: string;
  geo: string;
  topics: string;
  superseded_by: string;
};

const PATCH_DEFAULTS: PatchValues = {
  status: "active",
  beat: "",
  geo: "",
  topics: "",
  superseded_by: "",
};

const STATUS_OPTIONS = [
  { value: "active", label: "Active" },
  { value: "retracted", label: "Retracted" },
];

const COLUMNS: Column<Artifact>[] = [
  {
    key: "id",
    label: "ID",
    render: (row) => (
      <span
        title={row.id}
        style={{ fontFamily: "var(--mono)", fontSize: "0.8rem" }}
      >
        {row.id.slice(0, 14)}…
      </span>
    ),
  },
  { key: "stage", label: "Stage", render: (row) => row.stage },
  { key: "content_type", label: "Type", render: (row) => row.content_type },
  {
    key: "status",
    label: "Status",
    render: (row) => <StatusBadge value={row.status} />,
  },
  { key: "beat", label: "Beat", render: (row) => row.beat ?? "—" },
];

const SEARCH_FIELDS: (keyof Artifact)[] = [
  "stage",
  "content_type",
  "beat",
  "geo",
  "status",
];

export function ArtifactsTab() {
  const resource = useResource<Artifact>({
    list: api.listArtifacts,
    getId: (a) => a.id,
  });

  const { query, setQuery, filtered } = useFilter(resource.rows, SEARCH_FIELDS);
  const form = useForm<PatchValues>(PATCH_DEFAULTS);
  const { confirm, dialog } = useConfirm();
  const [editing, setEditing] = useState(false);

  const isSelected = resource.selected !== null;

  useEffect(() => {
    if (resource.selected) {
      form.setAll({
        status: resource.selected.status ?? "active",
        beat: resource.selected.beat ?? "",
        geo: resource.selected.geo ?? "",
        topics: (resource.selected.topics ?? []).join(", "),
        superseded_by: resource.selected.superseded_by ?? "",
      });
    } else {
      form.reset();
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setEditing(false);
    }
  }, [resource.selected]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSelect = (row: Artifact) => {
    resource.select(resource.selected?.id === row.id ? null : row);
    setEditing(false);
  };

  const handlePatch = () => {
    void resource.exec(
      () =>
        api.patchArtifact(resource.selected!.id, {
          status: form.values.status || null,
          beat: form.values.beat.trim() || null,
          geo: form.values.geo.trim() || null,
          topics: form.values.topics
            .split(",")
            .map((t) => t.trim())
            .filter(Boolean),
          superseded_by: form.values.superseded_by.trim() || null,
        }),
      { successMsg: "Artifact updated" },
    );
  };

  const handleRetract = async () => {
    const ok = await confirm({
      title: "Retract artifact",
      message:
        "Retract this artifact? It will be marked as retracted and excluded from analysis.",
      confirmLabel: "Retract",
      variant: "danger",
    });
    if (!ok) return;
    const done = await resource.exec(
      () => api.retractArtifact(resource.selected!.id),
      {
        successMsg: "Artifact retracted",
      },
    );
    if (done) resource.select(null);
  };

  const art = resource.selected;

  return (
    <div className="tab-page">
      {dialog}

      <div className="tab-header">
        <h2>Artifacts</h2>
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
              placeholder="Filter artifacts…"
            />
          </div>
          <div className="list-pane-body">
            <DataTable
              columns={COLUMNS}
              rows={filtered}
              selectedId={resource.selected?.id ?? null}
              getId={(a) => a.id}
              onSelect={handleSelect}
              emptyMessage="No artifacts in the store."
            />
          </div>
        </div>

        {/* Detail pane */}
        <div className="detail-pane">
          {!isSelected ? (
            <div className="detail-empty">
              Select an artifact to inspect or edit it.
            </div>
          ) : editing ? (
            <>
              <div className="detail-pane-header">
                <h3>Edit artifact</h3>
                <button className="secondary" onClick={() => setEditing(false)}>
                  ← View
                </button>
              </div>
              <div className="detail-pane-body">
                <SelectField
                  label="Status"
                  value={form.values.status}
                  onChange={(v) => form.set("status", v)}
                  options={STATUS_OPTIONS}
                />
                <TextField
                  label="Beat"
                  value={form.values.beat}
                  onChange={(v) => form.set("beat", v)}
                  placeholder="government:city-council"
                />
                <TextField
                  label="Geo"
                  value={form.values.geo}
                  onChange={(v) => form.set("geo", v)}
                  placeholder="us:il:springfield"
                />
                <TagField
                  label="Topics (comma-separated)"
                  value={form.values.topics}
                  onChange={(v) => form.set("topics", v)}
                  placeholder="zoning, housing"
                />
                <TextField
                  label="Superseded by (artifact ID)"
                  value={form.values.superseded_by}
                  onChange={(v) => form.set("superseded_by", v)}
                />
              </div>
              <div className="detail-pane-actions">
                <button
                  className="primary"
                  onClick={handlePatch}
                  disabled={resource.loading}
                >
                  Save changes
                </button>
              </div>
            </>
          ) : (
            <>
              <div className="detail-pane-header">
                <h3>Artifact details</h3>
                <button className="secondary" onClick={() => setEditing(true)}>
                  Edit
                </button>
              </div>
              <div className="detail-pane-body">
                <ReadOnlyField label="ID" value={art!.id} />
                <ReadOnlyField label="Stage" value={art!.stage} />
                <ReadOnlyField label="Content type" value={art!.content_type} />
                <ReadOnlyField label="Status" value={art!.status} />
                <ReadOnlyField label="Media type" value={art!.media_type} />
                <ReadOnlyField label="Beat" value={art!.beat} />
                <ReadOnlyField label="Geo" value={art!.geo} />
                <ReadOnlyField label="Source ID" value={art!.source_id} />
                <ReadOnlyField label="Event group" value={art!.event_group} />
                <ReadOnlyField
                  label="Assignment ID"
                  value={art!.assignment_id}
                />
                <ReadOnlyField label="Content URI" value={art!.content_uri} />
                <ReadOnlyField
                  label="Topics"
                  value={(art!.topics ?? []).join(", ") || null}
                />
                <ReadOnlyField
                  label="Derived from"
                  value={(art!.derived_from ?? []).join(", ") || null}
                />
                <ReadOnlyField
                  label="Superseded by"
                  value={art!.superseded_by}
                />
              </div>
              <div className="detail-pane-actions">
                <button
                  className="danger"
                  onClick={() => void handleRetract()}
                  disabled={resource.loading}
                >
                  Retract
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
