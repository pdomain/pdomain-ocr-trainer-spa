import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { ProfilesPage } from "./pages/ProfilesPage";

function App() {
  return (
    <BrowserRouter
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <div data-testid="app-root">
        <Routes>
          <Route path="/" element={<Navigate to="/profiles" replace />} />
          <Route path="/profiles" element={<ProfilesPage />} />
          <Route path="/profiles/:name" element={<ProfilesPage />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

export default App;
