import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Upload from "./pages/Upload";
import Jobs from "./pages/Jobs";
import Rankings from "./pages/Rankings";
import CandidateDetail from "./pages/CandidateDetail";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="upload" element={<Upload />} />
          <Route path="jobs" element={<Jobs />} />
          <Route path="rankings/:jobId?" element={<Rankings />} />
          <Route path="candidates/:candidateId" element={<CandidateDetail />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
