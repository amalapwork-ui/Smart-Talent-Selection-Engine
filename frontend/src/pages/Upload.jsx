import React, { useState, useEffect } from "react";
import toast from "react-hot-toast";
import UploadZone from "../components/UploadZone";
import { resumeApi } from "../services/api";

const STATUS_ICON = { done: "✅", processing: "⏳", pending: "🔵", error: "❌" };
const STATUS_COLOR = {
  done: "text-green-700 bg-green-50",
  processing: "text-yellow-700 bg-yellow-50",
  pending: "text-blue-700 bg-blue-50",
  error: "text-red-700 bg-red-50",
};

export default function Upload() {
  const [files, setFiles] = useState([]);
  const [jobRole, setJobRole] = useState("General");
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const [recentResumes, setRecentResumes] = useState([]);
  const [loadingResumes, setLoadingResumes] = useState(true);
  const [pollingIds, setPollingIds] = useState([]);

  const loadRecent = async () => {
    try {
      const res = await resumeApi.list({ ordering: "-upload_date" });
      setRecentResumes((res.data.results || res.data).slice(0, 20));
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingResumes(false);
    }
  };

  useEffect(() => { loadRecent(); }, []);

  // Poll for processing resumes
  useEffect(() => {
    if (pollingIds.length === 0) return;
    const interval = setInterval(async () => {
      await loadRecent();
      const res = await resumeApi.list({ ordering: "-upload_date" });
      const resumed = (res.data.results || res.data);
      const stillProcessing = resumed
        .filter((r) => pollingIds.includes(r.id) && ["pending", "processing"].includes(r.status))
        .map((r) => r.id);
      if (stillProcessing.length === 0) {
        setPollingIds([]);
        clearInterval(interval);
      }
    }, 3000);
    return () => clearInterval(interval);
  }, [pollingIds]);

  const handleFilesSelected = (newFiles) => {
    setFiles((prev) => {
      const existing = new Set(prev.map((f) => f.name + f.size));
      const unique = newFiles.filter((f) => !existing.has(f.name + f.size));
      return [...prev, ...unique];
    });
  };

  const removeFile = (index) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleUpload = async () => {
    if (files.length === 0) return;
    setUploading(true);
    setUploadResult(null);
    try {
      const res = await resumeApi.upload(files, jobRole);
      setUploadResult(res.data);
      setFiles([]);
      setPollingIds(res.data.created || []);
      await loadRecent();
    } catch (err) {
      setUploadResult({ error: err.response?.data || "Upload failed. Please retry." });
    } finally {
      setUploading(false);
    }
  };

  const handleReparse = async (id) => {
    await resumeApi.reparse(id);
    setPollingIds((prev) => [...prev, id]);
    await loadRecent();
  };

  const handleDeleteResume = async (id, filename) => {
    if (!window.confirm(`Delete "${filename}"? This cannot be undone.`)) return;
    const tid = toast.loading("Deleting...");
    try {
      await resumeApi.delete(id);
      setRecentResumes((prev) => prev.filter((r) => r.id !== id));
      toast.success("Resume deleted.", { id: tid });
    } catch {
      toast.error("Failed to delete resume.", { id: tid });
    }
  };

  return (
    <div className="space-y-8 max-w-4xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Upload Resumes</h1>
        <p className="text-gray-500 text-sm mt-1">Bulk upload PDF, DOCX, or image resumes for AI parsing</p>
      </div>

      {/* Job role */}
      <div className="card">
        <label className="block text-sm font-semibold text-gray-700 mb-2">Job Role / Batch Tag</label>
        <input
          value={jobRole}
          onChange={(e) => setJobRole(e.target.value)}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="e.g. Backend Engineer, Data Scientist..."
        />
        <p className="text-xs text-gray-400 mt-1">
          Group resumes by role for easier filtering and ranking.
        </p>
      </div>

      {/* Drop zone */}
      <UploadZone onFilesSelected={handleFilesSelected} />

      {/* File list */}
      {files.length > 0 && (
        <div className="card">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-gray-700">
              {files.length} file{files.length > 1 ? "s" : ""} selected
            </h3>
            <button onClick={() => setFiles([])} className="text-xs text-red-600 hover:underline">
              Clear all
            </button>
          </div>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {files.map((f, i) => (
              <div key={i} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                <div className="flex items-center gap-2">
                  <span className="text-lg">
                    {f.type === "application/pdf" ? "📄" :
                     f.name.endsWith(".docx") ? "📝" : "🖼️"}
                  </span>
                  <div>
                    <p className="text-sm text-gray-700 truncate max-w-xs">{f.name}</p>
                    <p className="text-xs text-gray-400">{(f.size / 1024).toFixed(1)} KB</p>
                  </div>
                </div>
                <button
                  onClick={() => removeFile(i)}
                  className="text-gray-400 hover:text-red-500 text-sm px-2"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
          <button
            onClick={handleUpload}
            disabled={uploading}
            className="btn-primary w-full mt-4"
          >
            {uploading ? (
              <span className="flex items-center justify-center gap-2">
                <span className="animate-spin">⏳</span> Uploading & Queuing...
              </span>
            ) : (
              `Upload ${files.length} Resume${files.length > 1 ? "s" : ""}`
            )}
          </button>
        </div>
      )}

      {/* Upload result */}
      {uploadResult && !uploadResult.error && (
        <div className="card border-green-200 bg-green-50">
          <h3 className="text-sm font-semibold text-green-800 mb-2">Upload Complete</h3>
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <p className="text-xl font-bold text-green-700">{uploadResult.total_queued}</p>
              <p className="text-xs text-green-600">Queued for parsing</p>
            </div>
            <div>
              <p className="text-xl font-bold text-yellow-600">{uploadResult.duplicates?.length || 0}</p>
              <p className="text-xs text-yellow-700">Duplicates skipped</p>
            </div>
            <div>
              <p className="text-xl font-bold text-red-600">{uploadResult.errors?.length || 0}</p>
              <p className="text-xs text-red-500">Errors</p>
            </div>
          </div>
        </div>
      )}

      {uploadResult?.error && (
        <div className="card border-red-200 bg-red-50">
          <p className="text-sm text-red-700">
            Upload failed: {typeof uploadResult.error === "string" ? uploadResult.error : JSON.stringify(uploadResult.error)}
          </p>
        </div>
      )}

      {/* Recent uploads */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-semibold text-gray-800">Recent Uploads</h2>
          <button onClick={loadRecent} className="text-xs text-blue-600 hover:underline">Refresh</button>
        </div>
        {loadingResumes ? (
          <p className="text-sm text-gray-400 text-center py-6">Loading...</p>
        ) : recentResumes.length === 0 ? (
          <p className="text-sm text-gray-400 text-center py-8">No resumes uploaded yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="text-left py-2 pr-4 text-xs font-medium text-gray-500">File</th>
                  <th className="text-left py-2 pr-4 text-xs font-medium text-gray-500">Role</th>
                  <th className="text-left py-2 pr-4 text-xs font-medium text-gray-500">Status</th>
                  <th className="text-left py-2 pr-4 text-xs font-medium text-gray-500">Confidence</th>
                  <th className="text-left py-2 text-xs font-medium text-gray-500">Date</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {recentResumes.map((r) => (
                  <tr key={r.id} className="border-b border-gray-50 hover:bg-gray-50">
                    <td className="py-2.5 pr-4">
                      <span className="font-medium text-gray-800 truncate max-w-[200px] block">{r.filename}</span>
                      <span className="text-xs text-gray-400">{r.file_size_kb} KB</span>
                    </td>
                    <td className="py-2.5 pr-4 text-gray-600">{r.job_role}</td>
                    <td className="py-2.5 pr-4">
                      <span className={`badge ${STATUS_COLOR[r.status]}`}>
                        {STATUS_ICON[r.status]} {r.status}
                      </span>
                      {r.error_message && (
                        <p className="text-xs text-red-500 mt-0.5 max-w-xs truncate">{r.error_message}</p>
                      )}
                    </td>
                    <td className="py-2.5 pr-4">
                      {r.parse_confidence > 0 ? (
                        <span className="text-gray-600">{(r.parse_confidence * 100).toFixed(0)}%</span>
                      ) : "—"}
                    </td>
                    <td className="py-2.5 text-gray-500 text-xs">
                      {new Date(r.upload_date).toLocaleDateString()}
                    </td>
                    <td className="py-2.5 pl-2">
                      <div className="flex items-center gap-2">
                        {r.status === "error" && (
                          <button
                            onClick={() => handleReparse(r.id)}
                            className="text-xs text-blue-600 hover:underline"
                          >
                            Retry
                          </button>
                        )}
                        <button
                          onClick={() => handleDeleteResume(r.id, r.filename)}
                          className="btn-danger text-xs py-1 px-2"
                          title="Delete resume"
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
