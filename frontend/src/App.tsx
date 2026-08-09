import { BrowserRouter, Routes, Route } from "react-router-dom";
import JobListPage from "./pages/JobListPage";
import JobDetailPage from "./pages/JobDetailPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<JobListPage />} />
        <Route path="/jobs/:id" element={<JobDetailPage />} />
      </Routes>
    </BrowserRouter>
  );
}
