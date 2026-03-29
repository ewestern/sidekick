import { useState, useEffect } from "react";
import type { ApiClient, ApiKeyIssuedResponse } from "../client/types.gen";
import { api } from "../lib/api";
import { useResource } from "../hooks/useResource";
import { useFilter } from "../hooks/useFilter";
import { useForm } from "../hooks/useForm";
import { useConfirm } from "../components/ui/ConfirmDialog";
import { useToast } from "../hooks/useToast";
import { DataTable, type Column } from "../components/ui/DataTable";
import { SearchInput } from "../components/ui/SearchInput";
import { StatusBadge } from "../components/ui/StatusBadge";
import {
  CheckboxGroup,
  ReadOnlyField,
  TagField,
  TextField,
} from "../components/ui/FieldRenderers";

const ROLE_OPTIONS = ["reader", "editor", "admin", "machine"];

type FormValues = {
  name: string;
  roles: string[];
  scopes: string;
  expires_at: string;
};

const DEFAULTS: FormValues = {
  name: "internal-admin-script",
  roles: ["admin"],
  scopes: "",
  expires_at: "",
};

function parseScopes(value: string): string[] {
  return value
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

function extractIssuedKey(data: unknown): ApiKeyIssuedResponse {
  if (!data || typeof data !== "object") {
    throw new Error("Invalid API response: expected issued key object.");
  }
  const maybe = data as Record<string, unknown>;
  if (typeof maybe.plaintext_key !== "string") {
    throw new Error(
      "Invalid API response: missing plaintext_key in issued key payload.",
    );
  }
  return data as ApiKeyIssuedResponse;
}

const COLUMNS: Column<ApiClient>[] = [
  { key: "name", label: "Name", render: (row) => row.name },
  {
    key: "key_prefix",
    label: "Prefix",
    render: (row) => (
      <span style={{ fontFamily: "var(--mono)", fontSize: "0.8rem" }}>
        {row.key_prefix}
      </span>
    ),
  },
  {
    key: "status",
    label: "Status",
    render: (row) => <StatusBadge value={row.status} />,
  },
  {
    key: "roles",
    label: "Roles",
    render: (row) => (row.roles ?? []).join(", ") || "—",
  },
  {
    key: "expires_at",
    label: "Expires",
    render: (row) =>
      row.expires_at ? new Date(row.expires_at).toLocaleDateString() : "Never",
  },
];

const SEARCH_FIELDS: (keyof ApiClient)[] = ["name", "status"];

export function ApiClientsTab() {
  const resource = useResource<ApiClient>({
    list: api.listApiClients,
    getId: (c) => c.id,
  });

  const { query, setQuery, filtered } = useFilter(resource.rows, SEARCH_FIELDS);
  const form = useForm<FormValues>(DEFAULTS);
  const { confirm, dialog } = useConfirm();
  const toast = useToast();
  const [issuedKey, setIssuedKey] = useState<ApiKeyIssuedResponse | null>(null);

  const isEditing = resource.selected !== null;

  useEffect(() => {
    if (resource.selected) {
      form.setAll({
        name: resource.selected.name,
        roles: resource.selected.roles ?? [],
        scopes: (resource.selected.scopes ?? []).join(", "),
        expires_at: resource.selected.expires_at ?? "",
      });
    } else {
      form.reset();
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setIssuedKey(null);
    }
  }, [resource.selected]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSelect = (row: ApiClient) => {
    resource.select(resource.selected?.id === row.id ? null : row);
    setIssuedKey(null);
  };

  const handleIssue = async () => {
    let result: unknown = null;
    const ok = await resource.exec(
      async () => {
        result = await api.createApiClient({
          name: form.values.name,
          roles: form.values.roles,
          scopes: parseScopes(form.values.scopes),
          expires_at: form.values.expires_at.trim() || null,
        });
        return result;
      },
      { successMsg: "API key issued", skipRefresh: true },
    );
    if (ok) {
      const issued = extractIssuedKey(result);
      setIssuedKey(issued);
      await resource.refresh();
    }
  };

  const handleRotate = async () => {
    const ok = await confirm({
      title: "Rotate API key",
      message: "This will invalidate the current key and issue a new one.",
      confirmLabel: "Rotate",
      variant: "default",
    });
    if (!ok) return;
    let result: unknown = null;
    const success = await resource.exec(
      async () => {
        result = await api.rotateApiClient(resource.selected!.id, {
          name: form.values.name.trim() || null,
          roles: form.values.roles,
          scopes: parseScopes(form.values.scopes),
          expires_at: form.values.expires_at.trim() || null,
        });
        return result;
      },
      { successMsg: "API key rotated", skipRefresh: true },
    );
    if (success) {
      const issued = extractIssuedKey(result);
      setIssuedKey(issued);
      await resource.refresh();
    }
  };

  const handleRevoke = async () => {
    const ok = await confirm({
      title: "Revoke API key",
      message: `Revoke key for "${resource.selected?.name}"? This cannot be undone.`,
      confirmLabel: "Revoke",
      variant: "danger",
    });
    if (!ok) return;
    const done = await resource.exec(
      () => api.revokeApiClient(resource.selected!.id),
      {
        successMsg: "API key revoked",
      },
    );
    if (done) resource.select(null);
  };

  return (
    <div className="tab-page">
      {dialog}
      {issuedKey && (
        <div
          className="dialog-overlay"
          onClick={() => setIssuedKey(null)}
          role="dialog"
          aria-modal="true"
          aria-labelledby="issued-key-title"
        >
          <div className="dialog" onClick={(e) => e.stopPropagation()}>
            <h3 id="issued-key-title" className="dialog-title">
              API key issued
            </h3>
            <p className="dialog-message">
              This is the only time the full key is shown. Copy and store it now.
            </p>
            <code className="key-banner-code">{issuedKey.plaintext_key}</code>
            <div className="dialog-actions">
              <button onClick={() => setIssuedKey(null)}>Close</button>
              <button
                className="primary"
                onClick={() => {
                  void navigator.clipboard.writeText(issuedKey.plaintext_key);
                  toast.success("Key copied to clipboard");
                }}
              >
                Copy key
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="tab-header">
        <h2>API Clients</h2>
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
              placeholder="Filter clients…"
            />
          </div>
          <div className="list-pane-body">
            <DataTable
              columns={COLUMNS}
              rows={filtered}
              selectedId={resource.selected?.id ?? null}
              getId={(c) => c.id}
              onSelect={handleSelect}
              emptyMessage="No API clients yet."
            />
          </div>
        </div>

        {/* Detail pane */}
        <div className="detail-pane">
          <div className="detail-pane-header">
            <h3>{isEditing ? "Manage client" : "Issue new key"}</h3>
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
            {/* Plaintext key banner */}
            {issuedKey && (
              <div className="key-banner">
                <p className="key-banner-title">
                  New key (shown once — copy now)
                </p>
                <code className="key-banner-code">
                  {issuedKey.plaintext_key}
                </code>
                <button
                  onClick={() => {
                    void navigator.clipboard.writeText(issuedKey.plaintext_key);
                    toast.success("Key copied to clipboard");
                  }}
                >
                  Copy key
                </button>
              </div>
            )}

            {/* Read-only details in edit mode */}
            {isEditing && (
              <>
                <ReadOnlyField
                  label="Client ID"
                  value={resource.selected!.id}
                />
                <ReadOnlyField
                  label="Key prefix"
                  value={resource.selected!.key_prefix}
                />
                <ReadOnlyField
                  label="Status"
                  value={resource.selected!.status}
                />
                <ReadOnlyField
                  label="Last used"
                  value={
                    resource.selected!.last_used_at
                      ? new Date(
                          resource.selected!.last_used_at,
                        ).toLocaleString()
                      : null
                  }
                />
                <ReadOnlyField
                  label="Created"
                  value={
                    resource.selected!.created_at
                      ? new Date(resource.selected!.created_at).toLocaleString()
                      : null
                  }
                />
                <hr
                  style={{
                    border: "none",
                    borderTop: "1px solid var(--border)",
                    margin: 0,
                  }}
                />
              </>
            )}

            <TextField
              label="Name"
              value={form.values.name}
              onChange={(v) => form.set("name", v)}
              placeholder="internal-admin-script"
            />
            <CheckboxGroup
              label="Roles"
              options={ROLE_OPTIONS}
              selected={form.values.roles}
              onChange={(v) => form.set("roles", v)}
            />
            <TagField
              label="Scopes (comma-separated)"
              value={form.values.scopes}
              onChange={(v) => form.set("scopes", v)}
              placeholder="read:artifacts, write:sources"
            />
            <TextField
              label="Expires at (ISO datetime)"
              value={form.values.expires_at}
              onChange={(v) => form.set("expires_at", v)}
              placeholder="2027-01-01T00:00:00Z"
            />
          </div>

          <div className="detail-pane-actions">
            {isEditing ? (
              <>
                <button
                  className="primary"
                  onClick={() => void handleRotate()}
                  disabled={resource.loading}
                >
                  Rotate key
                </button>
                <button
                  className="danger"
                  onClick={() => void handleRevoke()}
                  disabled={resource.loading}
                >
                  Revoke
                </button>
              </>
            ) : (
              <button
                className="primary"
                onClick={() => void handleIssue()}
                disabled={resource.loading}
              >
                Issue key
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
