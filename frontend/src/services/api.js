import axios from "axios";

// In development, Vite proxies /api → http://127.0.0.1:8000 (see vite.config.js).
// In production, set VITE_API_URL to your backend's full base URL.
const BASE_URL = import.meta.env.VITE_API_URL || "/api";

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 60000,
});

// ── Resumes ──────────────────────────────────────────────────────────────
export const resumeApi = {
  upload: (files, jobRole) => {
    const form = new FormData();
    files.forEach((f) => form.append("files", f));
    form.append("job_role", jobRole);
    return api.post("/resumes/upload/", form, {
      headers: { "Content-Type": "multipart/form-data" },
      onUploadProgress: (e) => e.onProgress?.(e),
    });
  },
  list: (params) => api.get("/resumes/", { params }),
  get: (id) => api.get(`/resumes/${id}/`),
  stats: () => api.get("/resumes/stats/"),
  reparse: (id) => api.post(`/resumes/${id}/reparse/`),
  delete: (id) => api.delete(`/resumes/${id}/`),
};

// ── Jobs ─────────────────────────────────────────────────────────────────
export const jobApi = {
  list: (params) => api.get("/jobs/", { params }),
  get: (id) => api.get(`/jobs/${id}/`),
  create: (data) => api.post("/jobs/", data),
  update: (id, data) => api.patch(`/jobs/${id}/`, data),
  delete: (id) => api.delete(`/jobs/${id}/`),
  runRanking: (id) => api.post(`/jobs/${id}/run-ranking/`),
  suggestJD: (id) => api.get(`/jobs/${id}/suggest-jd/`),
};

// ── Candidates ───────────────────────────────────────────────────────────
export const candidateApi = {
  list: (params) => api.get("/candidates/", { params }),
  get: (id) => api.get(`/candidates/${id}/`),
  delete: (id) => api.delete(`/candidates/${id}/`),
  vsJD: (candidateId, jobId) =>
    api.get(`/candidates/${candidateId}/vs-jd/`, { params: { job_id: jobId } }),
  feedback: (candidateId, data) =>
    api.post(`/candidates/${candidateId}/feedback/`, data),
  search: (q, k = 20) =>
    api.get("/candidates/search/", { params: { q, k } }),
};

// ── Rankings ─────────────────────────────────────────────────────────────
export const rankingApi = {
  results: (params) => api.get("/ranking/results/", { params }),
  runs: (params) => api.get("/ranking/runs/", { params }),
  quickRank: (jdText, limit = 50) =>
    api.post("/ranking/runs/quick-rank/", { jd_text: jdText, limit }),
};

export default api;
