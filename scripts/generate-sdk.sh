#!/usr/bin/env bash
# Generate the Sidekick API client SDK from the live OpenAPI spec.
#
# Usage:
#   scripts/generate-sdk.sh
#   SIDEKICK_API_URL=http://staging:8000 scripts/generate-sdk.sh
#
# Requires:
#   uv sync (run once from repo root to install dev dependencies)
#
# The API server must be running before calling this script.
# The generated source is written to packages/api-client/src/sidekick_client/.
# Review the diff and commit like any other code change.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PACKAGE_DIR="$REPO_ROOT/packages/api-client"
CONFIG="$PACKAGE_DIR/.openapi-python-client.yaml"
OPENAPI_URL="${SIDEKICK_API_URL:-http://localhost:8080}/openapi.json"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

echo "Fetching OpenAPI spec from $OPENAPI_URL ..."
uv run openapi-python-client generate \
    --url "$OPENAPI_URL" \
    --config "$CONFIG" \
    --output-path "$TMP" \
    --overwrite

echo "Installing generated source into $PACKAGE_DIR/src/sidekick_client/ ..."
rm -rf "$PACKAGE_DIR/src/sidekick_client"
cp -r "$TMP/sidekick_client" "$PACKAGE_DIR/src/"

echo "Done. Review the diff and commit."
