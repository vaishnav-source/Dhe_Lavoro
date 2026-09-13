import { BrowserRouter, Routes, Route } from "react-router-dom";
import JobListPage from "./pages/JobListPage";
import JobDetailPage from "./pages/JobDetailPage";
import TermsPage from "./pages/TermsPage";
import TermsGate from "./components/TermsGate";

export default function App() {
  return (
    <BrowserRouter>
      <TermsGate>
        <Routes>
          <Route path="/" element={<JobListPage />} />
          <Route path="/jobs/:id" element={<JobDetailPage />} />
          <Route path="/terms" element={<TermsPage />} />
        </Routes>
      </TermsGate>
    </BrowserRouter>
  );
}