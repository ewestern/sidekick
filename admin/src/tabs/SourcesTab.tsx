import type { Source, SourceStatus } from "../client/types.gen";
import { api } from "../lib/api";
import { useResource } from "../hooks/useResource";
import { useFilter } from "../hooks/useFilter";
import { DataTable, type Column } from "../components/ui/DataTable";
import { SearchInput } from "../components/ui/SearchInput";
import { StatusBadge } from "../components/ui/StatusBadge";
import { ReadOnlyField } from "../components/ui/FieldRenderers";

const COLUMNS: Column<Source>[] = [
  { key: "name", label: "Name", render: (row) => row.name },
  {
    key: "endpoint",
    label: "Endpoint",
    render: (row) => (
      <span
        title={row.endpoint ?? undefined}
        style={{ color: "var(--muted)", fontSize: "0.8rem" }}
      >
        {row.endpoint ?? "—"}
      </span>
    ),
  },
  {
    key: "status",
    label: "Status",
    render: (row) => <StatusBadge value={row.status} />,
  },
  {
    key: "source_tier",
    label: "Tier",
    render: (row) => <StatusBadge value={row.source_tier} />,
  },
  {
    key: "outlet",
    label: "Outlet",
    render: (row) => (
      <span
        title={row.outlet ?? undefined}
        style={{ color: "var(--muted)", fontSize: "0.8rem" }}
      >
        {row.outlet ?? "—"}
      </span>
    ),
  },
  { key: "beat", label: "Beat", render: (row) => row.beat ?? "—" },
  { key: "geo", label: "Geo", render: (row) => row.geo ?? "—" },
];

const SEARCH_FIELDS: (keyof Source)[] = [
  "name",
  "beat",
  "geo",
  "status",
  "source_tier",
  "outlet",
];

export function SourcesTab() {
  const resource = useResource<Source>({
    list: api.listSources,
    getId: (s) => s.id,
  });

  const { query, setQuery, filtered } = useFilter(resource.rows, SEARCH_FIELDS);

  const handleSelect = (row: Source) => {
    resource.select(resource.selected?.id === row.id ? null : row);
  };

  const src = resource.selected;

  const handleToggleStatus = (row: Source) => {
    const next: SourceStatus = row.status === "active" ? "inactive" : "active";
    void resource.exec(
      () => api.patchSource(row.id, { status: next }),
      {
        successMsg:
          next === "active" ? "Source activated" : "Source deactivated",
      },
    );
  };

  return (
    <div className="tab-page">
      <div className="tab-header">
        <h2>Sources</h2>
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
              placeholder="Filter sources…"
            />
          </div>
          <div className="list-pane-body">
            <DataTable
              columns={COLUMNS}
              rows={filtered}
              selectedId={resource.selected?.id ?? null}
              getId={(s) => s.id}
              onSelect={handleSelect}
              emptyMessage="No sources yet."
            />
          </div>
        </div>

        {/* Detail pane */}
        <div className="detail-pane">
          {!src ? (
            <div className="detail-empty">
              Select a source to view its details.
            </div>
          ) : (
            <>
              <div className="detail-pane-header">
                <h3>Source details</h3>
              </div>
              <div className="detail-pane-body">
                <ReadOnlyField label="ID" value={src.id} />
                <ReadOnlyField label="Name" value={src.name} />
                <ReadOnlyField label="Endpoint" value={src.endpoint} />
                <div className="readonly-field">
                  <span className="readonly-label">Status</span>
                  <div
                    className="readonly-value"
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "0.75rem",
                      flexWrap: "wrap",
                    }}
                  >
                    <StatusBadge value={src.status} />
                    <button
                      type="button"
                      className="secondary"
                      disabled={resource.loading}
                      onClick={() => handleToggleStatus(src)}
                    >
                      {src.status === "active" ? "Deactivate" : "Activate"}
                    </button>
                  </div>
                </div>
                <ReadOnlyField label="Source tier" value={src.source_tier} />
                <ReadOnlyField label="Outlet" value={src.outlet} />
                <ReadOnlyField label="Beat" value={src.beat} />
                <ReadOnlyField label="Geo" value={src.geo} />
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
