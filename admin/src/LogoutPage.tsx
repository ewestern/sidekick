import { useEffect, useState } from "react";
import { beginCognitoLogout } from "./lib/auth";

export function LogoutPage() {
  const [error, setError] = useState("");

  useEffect(() => {
    try {
      beginCognitoLogout();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Sign-out failed.");
    }
  }, []);

  return (
    <div className="center-screen">
      {error ? <p className="error">{error}</p> : <p>Signing you out...</p>}
    </div>
  );
}
