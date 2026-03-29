type TokenSet = {
  idToken: string;
  accessToken: string;
  refreshToken: string | null;
  expiresAt: number;
};

const TOKEN_KEY = "sidekick.admin.tokens";
const PKCE_VERIFIER_KEY = "sidekick.admin.pkce.verifier";
const PKCE_STATE_KEY = "sidekick.admin.pkce.state";

const cognitoDomain = import.meta.env.VITE_COGNITO_DOMAIN?.trim() ?? "";
const clientId = import.meta.env.VITE_COGNITO_CLIENT_ID?.trim() ?? "";
const redirectUri = import.meta.env.VITE_REDIRECT_URI?.trim() ?? "";
const logoutUri = import.meta.env.VITE_LOGOUT_URI?.trim() ?? "";

function assertAuthConfig(): void {
  if (!cognitoDomain || !clientId || !redirectUri || !logoutUri) {
    throw new Error(
      "Missing Cognito config. Set VITE_COGNITO_DOMAIN, VITE_COGNITO_CLIENT_ID, VITE_REDIRECT_URI, and VITE_LOGOUT_URI.",
    );
  }
}

function randomString(byteLength: number): string {
  const bytes = new Uint8Array(byteLength);
  window.crypto.getRandomValues(bytes);
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join(
    "",
  );
}

function toBase64Url(bytes: Uint8Array): string {
  const base64 = window.btoa(String.fromCharCode(...bytes));
  return base64.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

async function sha256Base64Url(input: string): Promise<string> {
  const encoder = new TextEncoder();
  const digest = await window.crypto.subtle.digest(
    "SHA-256",
    encoder.encode(input),
  );
  return toBase64Url(new Uint8Array(digest));
}

function buildAuthorizeUrl(state: string, challenge: string): string {
  const url = new URL(`https://${cognitoDomain}/oauth2/authorize`);
  url.searchParams.set("response_type", "code");
  url.searchParams.set("client_id", clientId);
  url.searchParams.set("redirect_uri", redirectUri);
  url.searchParams.set("scope", "openid email profile");
  url.searchParams.set("state", state);
  url.searchParams.set("code_challenge_method", "S256");
  url.searchParams.set("code_challenge", challenge);
  return url.toString();
}

function getTokenUrl(): string {
  return `https://${cognitoDomain}/oauth2/token`;
}

function saveTokens(tokens: TokenSet): void {
  localStorage.setItem(TOKEN_KEY, JSON.stringify(tokens));
}

function readTokens(): TokenSet | null {
  const raw = localStorage.getItem(TOKEN_KEY);
  if (!raw) {
    return null;
  }
  try {
    const parsed = JSON.parse(raw) as TokenSet;
    if (!parsed.idToken || !parsed.accessToken || !parsed.expiresAt) {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

function clearPkceState(): void {
  sessionStorage.removeItem(PKCE_VERIFIER_KEY);
  sessionStorage.removeItem(PKCE_STATE_KEY);
}

type TokenEndpointResponse = {
  id_token: string;
  access_token: string;
  refresh_token?: string;
  expires_in: number;
  token_type: string;
};

async function exchangeToken(
  params: URLSearchParams,
): Promise<TokenEndpointResponse> {
  const response = await fetch(getTokenUrl(), {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: params.toString(),
  });
  if (!response.ok) {
    throw new Error(`Token exchange failed (${response.status})`);
  }
  return (await response.json()) as TokenEndpointResponse;
}

function toTokenSet(
  payload: TokenEndpointResponse,
  existingRefresh: string | null,
): TokenSet {
  return {
    idToken: payload.id_token,
    accessToken: payload.access_token,
    refreshToken: payload.refresh_token ?? existingRefresh,
    expiresAt: Date.now() + payload.expires_in * 1000,
  };
}

export function isTokenValid(): boolean {
  const tokens = readTokens();
  if (!tokens) {
    return false;
  }
  const skewMs = 30_000;
  return tokens.expiresAt - skewMs > Date.now();
}

export function getIdToken(): string | null {
  const tokens = readTokens();
  return tokens?.idToken ?? null;
}

export function hasRefreshToken(): boolean {
  const tokens = readTokens();
  return Boolean(tokens?.refreshToken);
}

export async function login(): Promise<never> {
  assertAuthConfig();
  const verifier = randomString(64);
  const state = randomString(16);
  const challenge = await sha256Base64Url(verifier);
  sessionStorage.setItem(PKCE_VERIFIER_KEY, verifier);
  sessionStorage.setItem(PKCE_STATE_KEY, state);
  window.location.assign(buildAuthorizeUrl(state, challenge));
  throw new Error("Redirecting to sign in");
}

export async function handleCallback(
  code: string,
  state: string | null,
): Promise<void> {
  assertAuthConfig();
  const verifier = sessionStorage.getItem(PKCE_VERIFIER_KEY);
  const expectedState = sessionStorage.getItem(PKCE_STATE_KEY);
  if (!verifier || !expectedState || !state || state !== expectedState) {
    clearPkceState();
    throw new Error("Invalid sign-in callback state.");
  }

  const params = new URLSearchParams({
    grant_type: "authorization_code",
    client_id: clientId,
    code,
    redirect_uri: redirectUri,
    code_verifier: verifier,
  });
  const payload = await exchangeToken(params);
  saveTokens(toTokenSet(payload, null));
  clearPkceState();
}

export async function refreshTokens(): Promise<boolean> {
  assertAuthConfig();
  const current = readTokens();
  if (!current?.refreshToken) {
    return false;
  }
  const params = new URLSearchParams({
    grant_type: "refresh_token",
    client_id: clientId,
    refresh_token: current.refreshToken,
  });
  const payload = await exchangeToken(params);
  saveTokens(toTokenSet(payload, current.refreshToken));
  return true;
}

export function clearTokens(): void {
  localStorage.removeItem(TOKEN_KEY);
}

/**
 * Clears local session state and redirects to Cognito Hosted UI logout.
 * `logout_uri` must match an allowed sign-out URL in the Cognito app client (typically the SPA origin).
 */
export function beginCognitoLogout(): void {
  assertAuthConfig();
  clearTokens();
  clearPkceState();
  const url = new URL(`https://${cognitoDomain}/logout`);
  url.searchParams.set("client_id", clientId);
  url.searchParams.set("logout_uri", logoutUri);
  window.location.assign(url.toString());
}

function parseJwtPayload(token: string): Record<string, unknown> | null {
  const parts = token.split(".");
  if (parts.length < 2) {
    return null;
  }
  const padded = parts[1].replace(/-/g, "+").replace(/_/g, "/");
  const fixedPadding = padded + "=".repeat((4 - (padded.length % 4)) % 4);
  try {
    const json = window.atob(fixedPadding);
    return JSON.parse(json) as Record<string, unknown>;
  } catch {
    return null;
  }
}

export function getUserEmail(): string | null {
  const token = getIdToken();
  if (!token) {
    return null;
  }
  const payload = parseJwtPayload(token);
  const email = payload?.email;
  return typeof email === "string" ? email : null;
}
