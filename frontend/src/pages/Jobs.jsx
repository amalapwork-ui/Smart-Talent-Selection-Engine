import React, { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { jobApi } from "../services/api";
import JobForm from "../components/JobForm";

export default function Jobs() {
  const navigate = useNavigate();
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editJob, setEditJob] = useState(null);
  const [rankingJobId, setRankingJobId] = useState(null);
  const [suggestion, setSuggestion] = useState({ jobId: null, text: "", loading: false, error: false });

  const loadJobs = useCallback(async () => {
    setLoading(true);
    try {
      const res = await jobApi.list();
      setJobs(res.data.results || res.data);
    } catch {
      toast.error("Failed to load jobs.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadJobs(); }, [loadJobs]);

  const handleRunRanking = async (jobId) => {
    setRankingJobId(jobId);
    const tid = toast.loading("Starting ranking job...");
    try {
      await jobApi.runRanking(jobId);
      toast.success("Ranking started! Check the Rankings page for results.", { id: tid });
    } catch (err) {
      toast.error("Failed to start ranking: " + (err.response?.data?.detail || err.message), { id: tid });
    } finally {
      setRankingJobId(null);
    }
  };

  const handleSuggestJD = async (jobId) => {
    setSuggestion({ jobId, text: "", loading: true, error: false });
    try {
      const res = await jobApi.suggestJD(jobId);
      setSuggestion({ jobId, text: res.data.suggestions, loading: false, error: false });
    } catch (err) {
      const msg = err.response?.data?.error || "";
      const isKeyErr = msg.toLowerCase().includes("groq") || msg.toLowerCase().includes("api_key") || err.response?.status === 503;
      setSuggestion({
        jobId,
        loading: false,
        error: true,
        text: isKeyErr
          ? "AI suggestions unavailable. Please configure GROQ_API_KEY in backend/.env to enable this feature."
          : (msg || "Could not generate suggestions. Please try again."),
      });
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Delete this job? All ranking results will be removed.")) return;
    const tid = toast.loading("Deleting...");
    try {
      await jobApi.delete(id);
      toast.success("Job deleted.", { id: tid });
      loadJobs();
    } catch {
      toast.error("Delete failed.", { id: tid });
    }
  };

  const closeSuggestion = () => setSuggestion({ jobId: null, text: "", loading: false, error: false });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Jobs</h1>
          <p className="text-gray-500 text-sm mt-1">Manage job descriptions and run candidate rankings</p>
        </div>
        <button onClick={() => { setEditJob(null); setShowForm(true); }} className="btn-primary">
          + New Job
        </button>
      </div>

      {/* Modal */}
      {showForm && (
        <div
          className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4"
          onClick={(e) => { if (e.target === e.currentTarget) { setShowForm(false); setEditJob(null); } }}
        >
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-gray-900">{editJob ? "Edit Job" : "Create New Job"}</h2>
              <button onClick={() => { setShowForm(false); setEditJob(null); }} className="text-gray-400 hover:text-gray-700 text-2xl leading-none">&times;</button>
            </div>
            <JobForm
              initial={editJob}
              onSuccess={() => {
                setShowForm(false);
                setEditJob(null);
                loadJobs();
                toast.success(editJob ? "Job updated." : "Job created!");
              }}
              onCancel={() => { setShowForm(false); setEditJob(null); }}
            />
          </div>
        </div>
      )}

      {/* List */}
      {loading ? (
        <div className="text-center py-16 text-gray-400">
          <div className="inline-block w-6 h-6 border-4 border-blue-400 border-t-transparent rounded-full animate-spin mb-3" />
          <p>Loading jobs...</p>
        </div>
      ) : jobs.length === 0 ? (
        <div className="card text-center py-16">
          <div className="text-5xl mb-4">💼</div>
          <h3 className="text-lg font-semibold text-gray-700 mb-2">No jobs yet</h3>
          <p className="text-gray-400 text-sm mb-4">Create your first job to start ranking candidates</p>
          <button onClick={() => setShowForm(true)} className="btn-primary">+ Create Job</button>
        </div>
      ) : (
        <div className="space-y-4">
          {jobs.map((job) => (
            <div key={job.id} className="card space-y-4">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap mb-1">
                    <h3 className="text-base font-semibold text-gray-900">{job.title}</h3>
                    <span className={`badge ${job.is_active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                      {job.is_active ? "Active" : "Closed"}
                    </span>
                    {job.employment_type && (
                      <span className="badge bg-blue-50 text-blue-700">
                        {job.employment_type.replace("_", " ")}
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-gray-500 mb-2">
                    {job.department && <span>{job.department} &bull; </span>}
                    {job.location && <span>{job.location} &bull; </span>}
                    {job.min_experience_years > 0 && <span>{job.min_experience_years}+ yrs exp</span>}
                  </p>
                  <p className="text-sm text-gray-600 line-clamp-2">{job.description}</p>
                  {job.required_skills?.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {job.required_skills.slice(0, 8).map((s) => (
                        <span key={s} className="badge bg-blue-50 text-blue-700">{s}</span>
                      ))}
                      {job.required_skills.length > 8 && (
                        <span className="badge bg-gray-100 text-gray-500">+{job.required_skills.length - 8}</span>
                      )}
                    </div>
                  )}
                </div>
                <div className="text-right flex-shrink-0">
                  <p className="text-xl font-bold text-gray-900">{job.ranked_count}</p>
                  <p className="text-xs text-gray-400">candidates ranked</p>
                </div>
              </div>

              {/* Actions */}
              <div className="flex flex-wrap gap-2 pt-2 border-t border-gray-100">
                <button onClick={() => navigate("/rankings/" + job.id)} className="btn-secondary text-sm py-1.5">
                  View Rankings
                </button>
                <button onClick={() => handleRunRanking(job.id)} disabled={rankingJobId === job.id} className="btn-primary text-sm py-1.5">
                  {rankingJobId === job.id ? "Running..." : "Run Ranking"}
                </button>
                <button
                  onClick={() => suggestion.jobId === job.id ? closeSuggestion() : handleSuggestJD(job.id)}
                  disabled={suggestion.jobId === job.id && suggestion.loading}
                  className="btn-secondary text-sm py-1.5"
                >
                  {suggestion.jobId === job.id && suggestion.loading
                    ? "Generating..."
                    : suggestion.jobId === job.id
                    ? "Hide Suggestions"
                    : "Suggest Improvements"}
                </button>
                <button onClick={() => { setEditJob(job); setShowForm(true); }} className="btn-secondary text-sm py-1.5">Edit</button>
                <button onClick={() => handleDelete(job.id)} className="btn-danger text-sm py-1.5">
                  Delete
                </button>
              </div>

              {/* AI Suggestions panel */}
              {suggestion.jobId === job.id && !suggestion.loading && suggestion.text && (
                <div className={`rounded-xl p-4 border ${suggestion.error ? "bg-red-50 border-red-200" : "bg-amber-50 border-amber-200"}`}>
                  <div className="flex items-start justify-between gap-2">
                    <h4 className={`text-sm font-semibold ${suggestion.error ? "text-red-800" : "text-amber-800"}`}>
                      {suggestion.error ? "Could not generate suggestions" : "AI Suggestions"}
                    </h4>
                    <button onClick={closeSuggestion} className="text-gray-400 hover:text-gray-600 text-lg leading-none flex-shrink-0">&times;</button>
                  </div>
                  <p className={`text-sm mt-2 whitespace-pre-wrap leading-relaxed ${suggestion.error ? "text-red-700" : "text-amber-700"}`}>
                    {suggestion.text}
                  </p>
                  {suggestion.error && (
                    <button onClick={() => handleSuggestJD(job.id)} className="mt-2 text-xs text-red-600 hover:underline">
                      Retry
                    </button>
                  )}
                </div>
              )}
              {suggestion.jobId === job.id && suggestion.loading && (
                <div className="rounded-xl p-4 border bg-amber-50 border-amber-200">
                  <div className="flex items-center gap-2 text-sm text-amber-600">
                    <span className="inline-block w-4 h-4 border-2 border-amber-500 border-t-transparent rounded-full animate-spin" />
                    Generating AI suggestions via Groq...
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
