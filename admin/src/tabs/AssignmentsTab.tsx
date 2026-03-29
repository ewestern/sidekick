import { useEffect } from "react";
import type { Assignment } from "../client/types.gen";
import { api } from "../lib/api";
import { useResource } from "../hooks/useResource";
import { useFilter } from "../hooks/useFilter";
import { useForm } from "../hooks/useForm";
import { useConfirm } from "../components/ui/ConfirmDialog";
import { DataTable, type Column } from "../components/ui/DataTable";
import { SearchInput } from "../components/ui/SearchInput";
import { StatusBadge } from "../components/ui/StatusBadge";
import {
  SelectField,
  TextAreaField,
  TextField,
} from "../components/ui/FieldRenderers";

const TYPE_OPTIONS = [
  { value: "research", label: "Research" },
  { value: "coverage", label: "Coverage" },
  { value: "monitor", label: "Monitor" },
];

const STATUS_OPTIONS = [
  { value: "open", label: "Open" },
  { value: "in_progress", label: "In progress" },
  { value: "done", label: "Done" },
];

type FormValues = {
  id: string;
  type: string;
  status: string;
  query_text: string;
};

const DEFAULTS: FormValues = {
  id: "",
  type: "research",
  status: "open",
  query_text: "",
};

const COLUMNS: Column<Assignment>[] = [
  {
    key: "id",
    label: "ID",
    render: (row) => (
      <span
        title={row.id}
        style={{ fontFamily: "var(--mono)", fontSize: "0.8rem" }}
      >
        {row.id.slice(0, 12)}…
      </span>
    ),
  },
  { key: "type", label: "Type", render: (row) => row.type },
  {
    key: "status",
    label: "Status",
    render: (row) => <StatusBadge value={row.status} />,
  },
  {
    key: "query_text",
    label: "Query",
    render: (row) =>
      row.query_text.slice(0, 80) + (row.query_text.length > 80 ? "…" : ""),
  },
];

const SEARCH_FIELDS: (keyof Assignment)[] = ["type", "status", "query_text"];

export function AssignmentsTab() {
  const resource = useResource<Assignment>({
    list: api.listAssignments,
    getId: (a) => a.id,
  });

  const { query, setQuery, filtered } = useFilter(resource.rows, SEARCH_FIELDS);
  const form = useForm<FormValues>(DEFAULTS);
  const { confirm, dialog } = useConfirm();

  const isEditing = resource.selected !== null;

  useEffect(() => {
    if (resource.selected) {
      form.setAll({
        id: resource.selected.id,
        type: resource.selected.type,
        status: resource.selected.status ?? "open",
        query_text: resource.selected.query_text,
      });
    } else {
      form.reset();
    }
  }, [resource.selected]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSelect = (row: Assignment) => {
    resource.select(resource.selected?.id === row.id ? null : row);
  };

  const handleCreate = () => {
    void resource.exec(
      () =>
        api.createAssignment({
          id: form.values.id,
          type: form.values.type,
          status: form.values.status,
          query_text: form.values.query_text,
        }),
      { successMsg: "Assignment created" },
    );
  };

  const handleSave = () => {
    void resource.exec(
      () =>
        api.patchAssignment(resource.selected!.id, {
          status: form.values.status || null,
          query_text: form.values.query_text || null,
        }),
      { successMsg: "Assignment updated" },
    );
  };

  const handleDelete = async () => {
    const ok = await confirm({
      title: "Delete assignment",
      message: "Delete this assignment? This cannot be undone.",
      confirmLabel: "Delete",
      variant: "danger",
    });
    if (!ok) return;
    const deleted = await resource.exec(
      () => api.deleteAssignment(resource.selected!.id),
      {
        successMsg: "Assignment deleted",
      },
    );
    if (deleted) resource.select(null);
  };

  return (
    <div className="tab-page">
      {dialog}

      <div className="tab-header">
        <h2>Assignments</h2>
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
              placeholder="Filter assignments…"
            />
          </div>
          <div className="list-pane-body">
            <DataTable
              columns={COLUMNS}
              rows={filtered}
              selectedId={resource.selected?.id ?? null}
              getId={(a) => a.id}
              onSelect={handleSelect}
              emptyMessage="No assignments yet."
            />
          </div>
        </div>

        {/* Detail pane */}
        <div className="detail-pane">
          <div className="detail-pane-header">
            <h3>{isEditing ? "Edit assignment" : "New assignment"}</h3>
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
              label="Assignment ID"
              value={form.values.id}
              onChange={(v) => form.set("id", v)}
              placeholder="asgn_abc123"
              readOnly={isEditing}
            />
            <SelectField
              label="Type"
              value={form.values.type}
              onChange={(v) => form.set("type", v)}
              options={TYPE_OPTIONS}
            />
            <SelectField
              label="Status"
              value={form.values.status}
              onChange={(v) => form.set("status", v)}
              options={STATUS_OPTIONS}
            />
            <TextAreaField
              label="Query"
              value={form.values.query_text}
              onChange={(v) => form.set("query_text", v)}
              placeholder="What do we know about the proposed school closure on Maple Street?"
              rows={5}
            />
          </div>

          <div className="detail-pane-actions">
            {isEditing ? (
              <>
                <button
                  className="primary"
                  onClick={handleSave}
                  disabled={resource.loading}
                >
                  Save changes
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
              <button
                className="primary"
                onClick={handleCreate}
                disabled={resource.loading}
              >
                Create assignment
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
