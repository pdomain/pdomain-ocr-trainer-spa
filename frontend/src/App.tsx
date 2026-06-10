import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
  useNavigate,
} from "react-router-dom";
import {
  AppShell,
  SuiteSiblingsProvider,
  createApiUIPrefsConfig,
} from "@pdomain/pdomain-ui/shell";
import { ShortcutsProvider } from "@pdomain/pdomain-ui/hooks";
import type { InstalledApp, LaunchResult } from "@pdomain/pdomain-ui/shell";

import { ProfilesPage } from "./pages/ProfilesPage";
import { ProfileDetailPage } from "./pages/ProfileDetailPage";
import { DatasetsPage } from "./pages/DatasetsPage";
import { TypefaceKanbanPage } from "./pages/TypefaceKanbanPage";
import { RunListPage } from "./pages/RunListPage";
import { RunDetailPage } from "./pages/RunDetailPage";
import { NewRunPage } from "./pages/NewRunPage";
import { ModelsPage } from "./pages/ModelsPage";
import { ModelDetailPage } from "./pages/ModelDetailPage";
import { EvalFormPage } from "./pages/EvalFormPage";
import { EvalResultPage } from "./pages/EvalResultPage";
import { PublishPage } from "./pages/PublishPage";
import { AppToaster } from "./components/AppToaster";
import { BannerStack } from "./components/BannerStack";
import { TrainerHeader } from "./shell/TrainerHeader";
import { TrainerRail } from "./shell/TrainerRail";
import { useTrainerJobs, makeJobsProps } from "./shell/useTrainerJobs";
import { useTrainerShortcuts } from "./shell/useTrainerShortcuts";
import { getAppEnv } from "./lib/appEnv";
import { trainerSettingsPanels } from "./shell/trainerSettingsPanels";

const uiPrefsConfig = createApiUIPrefsConfig("/api/ui-prefs");

const fetchInstalled = async (): Promise<InstalledApp[]> => {
  try {
    const res = await fetch("/api/suite/installed");
    if (!res.ok) return [];
    return (await res.json()) as InstalledApp[];
  } catch {
    return [];
  }
};

const postLaunch = async (id: string): Promise<LaunchResult> => {
  try {
    const res = await fetch("/api/suite/launch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id }),
    });
    if (!res.ok) return { kind: "requires-host-config", siblingId: id };
    return (await res.json()) as LaunchResult;
  } catch {
    return { kind: "requires-host-config", siblingId: id };
  }
};

function AppRoutes(): React.JSX.Element {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/profiles" replace />} />
      <Route path="/profiles" element={<ProfilesPage />} />
      <Route path="/profiles/:name" element={<ProfileDetailPage />} />
      <Route
        path="/profiles/:name/datasets/typeface-classification"
        element={<TypefaceKanbanPage />}
      />
      <Route path="/profiles/:name/datasets/:task" element={<DatasetsPage />} />
      <Route path="/runs" element={<RunListPage />} />
      <Route path="/runs/new" element={<NewRunPage />} />
      <Route path="/runs/:runId" element={<RunDetailPage />} />
      <Route path="/models" element={<ModelsPage />} />
      <Route path="/models/:name" element={<ModelDetailPage />} />
      <Route path="/eval" element={<EvalFormPage />} />
      <Route path="/eval/:runId/result" element={<EvalResultPage />} />
      <Route path="/publish" element={<PublishPage />} />
    </Routes>
  );
}

function AppShellWithHeader(): React.JSX.Element {
  const { pill, dock } = useTrainerJobs();
  const navigate = useNavigate();
  useTrainerShortcuts();
  const env = getAppEnv();
  const jobsProps = makeJobsProps(dock, (id) => navigate(`/runs/${id}`));
  return (
    <AppShell
      appId="pdomain-ocr-trainer-spa"
      appDisplayName="OCR Trainer"
      appIconUrl="/api/self/icons/32"
      deployMode="local"
      launcherSlot="header"
      uiPrefsConfig={uiPrefsConfig}
      settingsPanels={trainerSettingsPanels}
      jobs={jobsProps}
      header={<TrainerHeader activeJobs={pill} appVersion={env.version} />}
      rail={<TrainerRail />}
      main={
        <>
          <BannerStack />
          <AppRoutes />
        </>
      }
    />
  );
}

export default function App(): React.JSX.Element {
  return (
    <BrowserRouter
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <SuiteSiblingsProvider value={{ fetchInstalled, postLaunch }}>
        <ShortcutsProvider>
          <AppShellWithHeader />
          <AppToaster />
        </ShortcutsProvider>
      </SuiteSiblingsProvider>
    </BrowserRouter>
  );
}
