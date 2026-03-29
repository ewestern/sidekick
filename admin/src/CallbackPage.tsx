import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { handleCallback } from "./lib/auth";
import { configureApi } from "./lib/api";

export function CallbackPage() {
  const navigate = useNavigate();
  const [error, setError] = useState("");

  useEffect(() => {
    async function completeCallback(): Promise<void> {
      const params = new URLSearchParams(window.location.search);
      const code = params.get("code");
      const state = params.get("state");
      if (!code) {
        setError("Missing authorization code in callback URL.");
        return;
      }
      try {
        await handleCallback(code, state);
        configureApi();
        navigate("/sources", { replace: true });
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : "Sign-in failed.");
      }
    }

    void completeCallback();
  }, [navigate]);

  return (
    <div className="center-screen">
      {error ? <p className="error">{error}</p> : <p>Signing you in...</p>}
    </div>
  );
}
