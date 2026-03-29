/**
 * Resolve reader-facing CMS geo slug from the Host header.
 * Examples: shasta.sidekick.news → shasta; shasta.localhost:3000 → shasta
 */
export function parseGeoSlugFromHost(host: string | null): string | null {
  if (!host) {
    return null;
  }
  const hostname = host.split(":")[0]?.toLowerCase() ?? "";
  if (hostname === "localhost" || hostname === "127.0.0.1") {
    return process.env.DEFAULT_CMS_GEO_SLUG ?? "local";
  }
  const parts = hostname.split(".");
  if (parts.length >= 3 && parts[0] && parts[0] !== "www") {
    return parts[0];
  }
  if (parts.length === 2 && parts[1] === "localhost" && parts[0]) {
    return parts[0];
  }
  return null;
}
