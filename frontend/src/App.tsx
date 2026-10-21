import { BrowserRouter, Routes, Route, Outlet } from "react-router-dom";
import JobListPage from "./pages/JobListPage";
import JobDetailPage from "./pages/JobDetailPage";
import TermsPage from "./pages/TermsPage";
import TermsGate from "./components/TermsGate";
import OfflineGate from "./components/OfflineGate";

// Layout wrapper applying both Offline and Terms gates to child routes
function ProtectedLayout() {
  return (
    <OfflineGate>
      <TermsGate>
        <Outlet />
      </TermsGate>
    </OfflineGate>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public Route (Accessible offline or before accepting terms) */}
        <Route path="/terms" element={<TermsPage />} />

        {/* Protected Routes (Wrapped by both gates) */}
        <Route element={<ProtectedLayout />}>
          <Route path="/" element={<JobListPage />} />
          <Route path="/jobs/:id" element={<JobDetailPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}