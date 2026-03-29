import { useEffect, useState, type ReactNode } from "react";
import {
  hasRefreshToken,
  isTokenValid,
  login,
  refreshTokens,
} from "../lib/auth";
import { configureApi } from "../lib/api";

type AuthGuardProps = {
  children: ReactNode;
};

export function AuthGuard({ children }: AuthGuardProps) {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function ensureAuthenticated(): Promise<void> {
      try {
        if (!isTokenValid()) {
          if (hasRefreshToken()) {
            const refreshed = await refreshTokens();
            if (!refreshed) {
              await login();
              return;
            }
          } else {
            await login();
            return;
          }
        }
        configureApi();
        if (!cancelled) {
          setReady(true);
        }
      } catch {
        await login();
      }
    }

    void ensureAuthenticated();
    return () => {
      cancelled = true;
    };
  }, []);

  if (!ready) {
    return (
      <div className="center-screen">
        <p>Checking session...</p>
      </div>
    );
  }

  return <>{children}</>;
}
