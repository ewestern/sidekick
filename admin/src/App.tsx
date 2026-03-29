import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/AppShell.js";
import { AuthGuard } from "./components/AuthGuard.js";
import { CallbackPage } from "./CallbackPage.js";
import { LogoutPage } from "./LogoutPage.js";
import { AgentConfigsTab } from "./tabs/AgentConfigsTab.js";
import { ApiClientsTab } from "./tabs/ApiClientsTab.js";
import { ArtifactsTab } from "./tabs/ArtifactsTab.js";
import { AssignmentsTab } from "./tabs/AssignmentsTab.js";
import { SourcesTab } from "./tabs/SourcesTab.js";
import { ToastContext, useToastState } from "./hooks/useToast.js";
import "./App.css";
import "./css/layout.css";
import "./css/table.css";
import "./css/form.css";
import "./css/toast.css";
import "./css/dialog.css";
import "./css/badges.css";

function App() {
  const toastState = useToastState();

  return (
    <ToastContext.Provider value={toastState}>
      <BrowserRouter>
        <Routes>
          <Route path="/callback" element={<CallbackPage />} />
          <Route path="/logout" element={<LogoutPage />} />
          <Route
            path="/"
            element={
              <AuthGuard>
                <AppShell />
              </AuthGuard>
            }
          >
            <Route index element={<Navigate to="/sources" replace />} />
            <Route path="sources" element={<SourcesTab />} />
            <Route path="assignments" element={<AssignmentsTab />} />
            <Route path="agent-configs" element={<AgentConfigsTab />} />
            <Route path="artifacts" element={<ArtifactsTab />} />
            <Route path="api-clients" element={<ApiClientsTab />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ToastContext.Provider>
  );
}

export default App;
