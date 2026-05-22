import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { ProfilesPage } from "./pages/ProfilesPage";
import { ProfileDetailPage } from "./pages/ProfileDetailPage";
import { DatasetsPage } from "./pages/DatasetsPage";
import { RunListPage } from "./pages/RunListPage";
import { RunDetailPage } from "./pages/RunDetailPage";
import { NewRunPage } from "./pages/NewRunPage";
import { ModelsPage } from "./pages/ModelsPage";
import { ModelDetailPage } from "./pages/ModelDetailPage";
import { EvalFormPage } from "./pages/EvalFormPage";
import { EvalResultPage } from "./pages/EvalResultPage";
import { PublishPage } from "./pages/PublishPage";
import { AppChrome } from "./components/AppChrome";
import { AppToaster } from "./components/AppToaster";

function App() {
  return (
    <BrowserRouter
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <div data-testid="app-root">
        <AppChrome />
        <Routes>
          <Route path="/" element={<Navigate to="/profiles" replace />} />
          <Route path="/profiles" element={<ProfilesPage />} />
          <Route path="/profiles/:name" element={<ProfileDetailPage />} />
          <Route
            path="/profiles/:name/datasets/:task"
            element={<DatasetsPage />}
          />
          <Route path="/runs" element={<RunListPage />} />
          <Route path="/runs/new" element={<NewRunPage />} />
          <Route path="/runs/:runId" element={<RunDetailPage />} />
          <Route path="/models" element={<ModelsPage />} />
          <Route path="/models/:name" element={<ModelDetailPage />} />
          <Route path="/eval" element={<EvalFormPage />} />
          <Route path="/eval/:runId/result" element={<EvalResultPage />} />
          <Route path="/publish" element={<PublishPage />} />
        </Routes>
      </div>
      <AppToaster />
    </BrowserRouter>
  );
}

export default App;
