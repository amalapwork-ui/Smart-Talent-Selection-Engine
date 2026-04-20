import React, { useState, useEffect } from "react";
import { useParams, useSearchParams, useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { candidateApi, jobApi } from "../services/api";
import ScoreBreakdown from "../components/ScoreBreakdown";

function Section({ title, children }) {
  return (
    <div className="card">
      <h3 className="text-base font-semibold text-gray-800 mb-4">{title}</h3>
      {children}
    </div>
  );
}

function Tag({ label, color = "blue" }) {
  const colors = {
    blue: "bg-blue-50 text-blue-700",
    green: "bg-green-100 text-green-700",
    red: "bg-red-100 text-red-700",
    gray: "bg-gray-100 text-gray-600",
  };
  return <span className={`badge ${colors[color]}`}>{label}</span>;
}

// Decision badge config
const DECISION = {
  hired:       { label: "Hired",              cls: "bg-green-100 text-green-700" },
  shortlisted: { label: "Shortlisted",        cls: "bg-yellow-100 text-yellow-700" },
  interview:   { label: "Called for Interview", cls: "bg-blue-100 text-blue-700" },
  rejected:    { label: "Rejected",           cls: "bg-red-100 text-red-700" },
};

function DecisionBadge({ action }) {
  const d = DECISION[action];
  if (!d) return null;
  return <span className={`badge ${d.cls}`}>{d.label}</span>;
}

/**
 * Fetches the resume file via fetch() (goes through Vite proxy, no iframe/CORS issues)
 * and renders it as a blob: URL inside an iframe or img tag.
 * This sidesteps X-Frame-Options and cross-port proxy problems entirely.
 */
function ResumeViewer({ url, fileType, filename }) {
  const [blobUrl, setBlobUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!url) return;
    const ext = (fileType || "").toLowerCase().replace(".", "");
    if (!["pdf", "jpg", "jpeg", "png"].includes(ext)) return;

    let objectUrl = null;
    setLoading(true);
    setError(false);
    setBlobUrl(null);

    fetch(url)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.blob();
      })
      .then((blob) => {
        objectUrl = URL.createObjectURL(blob);
        setBlobUrl(objectUrl);
        setLoading(false);
      })
      .catch((err) => {
        console.error("ResumeViewer fetch error:", err);
        setError(true);
        setLoading(false);
      });

    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [url, fileType]);

  if (!url) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-gray-400 bg-gray-50 rounded-xl border border-dashed border-gray-200">
        <div className="text-4xl mb-3">📄</div>
        <p className="text-sm">Resume file not available</p>
      </div>
    );
  }

  const ext = (fileType || "").toLowerCase().replace(".", "");
  const isViewable = ["pdf", "jpg", "jpeg", "png"].includes(ext);
  const isPDF = ext === "pdf";

  if (!isViewable) {
    return (
      <div className="flex flex-col items-center justify-center h-48 text-gray-500 bg-gray-50 rounded-xl border border-dashed border-gray-200 gap-3">
        <div className="text-4xl">📝</div>
        <p className="text-sm">
          <span className="font-medium">{ext.toUpperCase()}</span> files can't be previewed in the browser
        </p>
        <a href={url} download={filename} className="btn-secondary text-sm py-1.5 px-4">
          Download {filename || "Resume"}
        </a>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 bg-gray-50 rounded-xl border border-gray-200">
        <div className="flex items-center gap-2 text-gray-400">
          <div className="w-5 h-5 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
          <span className="text-sm">Loading resume...</span>
        </div>
      </div>
    );
  }

  if (error || !blobUrl) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-gray-400 bg-gray-50 rounded-xl border border-dashed border-gray-200 gap-3">
        <div className="text-4xl">⚠️</div>
        <p className="text-sm">Could not load resume file</p>
        <a href={url} target="_blank" rel="noreferrer" className="btn-secondary text-sm py-1.5 px-4">
          Open in new tab ↗
        </a>
      </div>
    );
  }

  if (!isPDF) {
    return (
      <div className="flex justify-center">
        <img
          src={blobUrl}
          alt={filename || "Resume"}
          className="max-w-full rounded-xl shadow border border-gray-200"
        />
      </div>
    );
  }

  return (
    <iframe
      src={blobUrl}
      title={filename || "Resume"}
      className="w-full rounded-xl border border-gray-200 shadow-sm"
      style={{ height: "820px" }}
    />
  );
}

export default function CandidateDetail() {
  const { candidateId } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const jobId = searchParams.get("job_id");

  const [candidate, setCandidate] = useState(null);
  const [comparison, setComparison] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [selectedJobId, setSelectedJobId] = useState(jobId || "");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [feedback, setFeedback] = useState({ action: "", notes: "" });
  const [feedbackSent, setFeedbackSent] = useState(false);
  const [activeTab, setActiveTab] = useState("overview");

  const refetchCandidate = async () => {
    try {
      const res = await candidateApi.get(candidateId);
      setCandidate(res.data);
      // Pre-populate feedback form with the latest saved decision
      if (res.data.latest_feedback_action) {
        setFeedback((f) => ({ ...f, action: res.data.latest_feedback_action }));
      }
    } catch { /* non-fatal */ }
  };

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError(false);
      try {
        const [candRes, jobsRes] = await Promise.all([
          candidateApi.get(candidateId),
          jobApi.list(),
        ]);
        const cand = candRes.data;
        setCandidate(cand);
        setJobs(jobsRes.data.results || jobsRes.data);
        // Pre-populate form with latest saved decision
        if (cand.latest_feedback_action) {
          setFeedback((f) => ({ ...f, action: cand.latest_feedback_action }));
        }
      } catch (err) {
        console.error(err);
        setError(true);
        toast.error("Failed to load candidate profile.");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [candidateId]);

  useEffect(() => {
    const loadComparison = async () => {
      if (!selectedJobId || !candidateId) return;
      try {
        const res = await candidateApi.vsJD(candidateId, selectedJobId);
        setComparison(res.data);
      } catch {
        setComparison(null);
      }
    };
    loadComparison();
  }, [selectedJobId, candidateId]);

  const handleFeedback = async () => {
    if (!feedback.action || !selectedJobId) return;
    const tid = toast.loading("Submitting feedback...");
    try {
      await candidateApi.feedback(candidateId, {
        action: feedback.action,
        notes: feedback.notes,
        job_id: selectedJobId,
      });
      setFeedbackSent(true);
      // Refetch so badge + is_shortlisted update immediately
      await refetchCandidate();
      toast.success("Feedback submitted!", { id: tid });
    } catch (err) {
      const msg = err.response?.data?.error || err.response?.data?.detail || "Failed to submit feedback.";
      toast.error(msg, { id: tid });
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="inline-block w-8 h-8 border-4 border-blue-400 border-t-transparent rounded-full animate-spin mb-3" />
          <p className="text-gray-400 text-sm">Loading candidate...</p>
        </div>
      </div>
    );
  }

  if (error || !candidate) {
    return (
      <div className="text-center py-16">
        <div className="text-5xl mb-4">😕</div>
        <p className="text-gray-600 font-medium mb-1">Candidate not found</p>
        <p className="text-gray-400 text-sm mb-4">The profile may have been deleted or the ID is invalid.</p>
        <button onClick={() => navigate(-1)} className="btn-secondary">← Go Back</button>
      </div>
    );
  }

  const profile = candidate.structured_profile || {};
  const contact = profile.contact || {};
  const skillCategories = profile.skill_categories || {};
  const skills = Array.isArray(profile.skills) ? profile.skills : [];
  const experience = profile.experience_years || {};
  const projects = Array.isArray(profile.projects) ? profile.projects : [];
  const education = Array.isArray(profile.education) ? profile.education : [];
  const certifications = Array.isArray(profile.certifications) ? profile.certifications : [];

  const TABS = ["overview", "resume", "skills", "experience", "comparison", "feedback"];

  return (
    <div className="space-y-6 max-w-5xl">
      {/* Header */}
      <div className="flex items-start gap-4">
        <button
          onClick={() => navigate(-1)}
          className="btn-secondary text-sm py-1.5 flex items-center gap-1 flex-shrink-0"
        >
          ← Back
        </button>
        <div className="flex-1">
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-2xl font-bold text-gray-900">
              {candidate.candidate_name || `Candidate #${candidateId}`}
            </h1>
            <DecisionBadge action={candidate.latest_feedback_action} />
          </div>
          <p className="text-gray-500 text-sm mt-1">
            {contact.email && <span className="mr-3">{contact.email}</span>}
            {contact.phone && <span>{contact.phone}</span>}
          </p>
          <p className="text-xs text-gray-400 mt-1">
            {candidate.resume_filename}
            {candidate.resume_job_role && ` • ${candidate.resume_job_role}`}
          </p>
        </div>

        {candidate.latest_score && (
          <div className="text-center bg-blue-50 rounded-xl px-4 py-3 flex-shrink-0">
            <p className="text-2xl font-bold text-blue-700">
              {candidate.latest_score.total?.toFixed(1)}%
            </p>
            <p className="text-xs text-blue-500">{candidate.latest_score.job_title}</p>
          </div>
        )}
      </div>

      {/* Summary */}
      {profile.summary && (
        <div className="card bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-100">
          <p className="text-sm text-gray-700 leading-relaxed italic">"{profile.summary}"</p>
        </div>
      )}

      {/* Job selector for comparison */}
      <div className="flex items-center gap-3">
        <label className="text-sm font-medium text-gray-700 whitespace-nowrap">Compare with job:</label>
        <select
          value={selectedJobId}
          onChange={(e) => setSelectedJobId(e.target.value)}
          className="flex-1 max-w-xs border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">Select a job...</option>
          {jobs.map((j) => (
            <option key={j.id} value={j.id}>{j.title}</option>
          ))}
        </select>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-200 overflow-x-auto">
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-sm font-medium capitalize whitespace-nowrap transition-colors border-b-2 -mb-px ${
              activeTab === tab
                ? "border-blue-600 text-blue-700"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* ── Overview ─────────────────────────────────────────────── */}
      {activeTab === "overview" && (
        <div className="grid grid-cols-2 gap-6">
          <Section title="📋 Quick Stats">
            <div className="space-y-3">
              {[
                ["Total Experience", `${candidate.total_experience_years} years`],
                ["Skills Found",    skills.length],
                ["Projects",        projects.length],
                ["Certifications",  certifications.length],
                ["Extraction",      profile.extraction_method],
              ].map(([label, val]) => val !== undefined && val !== "" && (
                <div key={label} className="flex justify-between text-sm">
                  <span className="text-gray-500">{label}</span>
                  <span className="font-semibold text-xs text-right">{val}</span>
                </div>
              ))}
            </div>
          </Section>

          <Section title="🎓 Education">
            {education.length > 0 ? (
              <div className="space-y-2">
                {education.map((edu, i) => (
                  <div key={i} className="text-sm">
                    <p className="font-medium text-gray-800">
                      {typeof edu === "string" ? edu : edu.degree || edu.context || JSON.stringify(edu)}
                    </p>
                    {edu.institution && <p className="text-gray-500">{edu.institution}</p>}
                    {edu.year && <p className="text-gray-400">{edu.year}</p>}
                  </div>
                ))}
              </div>
            ) : <p className="text-sm text-gray-400">No education data extracted</p>}
          </Section>

          <Section title="🏆 Certifications">
            {certifications.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {certifications.map((c, i) => (
                  <Tag key={i} label={typeof c === "string" ? c : JSON.stringify(c)} color="green" />
                ))}
              </div>
            ) : <p className="text-sm text-gray-400">No certifications found</p>}
          </Section>

          {comparison?.ranking && comparison.ranking.total_score != null && (
            <Section title="📊 Score Breakdown">
              <ScoreBreakdown result={comparison.ranking} />
            </Section>
          )}
        </div>
      )}

      {/* ── Resume ───────────────────────────────────────────────── */}
      {activeTab === "resume" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-gray-700">
              {candidate.resume_filename}
              {candidate.resume_file_type && (
                <span className="ml-2 badge bg-gray-100 text-gray-500 uppercase text-xs">
                  {candidate.resume_file_type.replace(".", "")}
                </span>
              )}
            </h2>
            {candidate.resume_url && (
              <a
                href={candidate.resume_url}
                target="_blank"
                rel="noreferrer"
                className="btn-secondary text-sm py-1.5"
              >
                Open in new tab ↗
              </a>
            )}
          </div>
          <ResumeViewer
            url={candidate.resume_url}
            fileType={candidate.resume_file_type}
            filename={candidate.resume_filename}
          />
        </div>
      )}

      {/* ── Skills ───────────────────────────────────────────────── */}
      {activeTab === "skills" && (
        <div className="space-y-6">
          {Object.keys(skillCategories).length > 0 && (
            <Section title="🗂 Skills by Domain">
              <div className="space-y-4">
                {Object.entries(skillCategories).map(([domain, domainSkills]) => (
                  <div key={domain}>
                    <p className="text-xs font-semibold text-gray-500 uppercase mb-2">{domain}</p>
                    <div className="flex flex-wrap gap-1.5">
                      {(Array.isArray(domainSkills) ? domainSkills : []).map((s) => (
                        <Tag key={s} label={s} />
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </Section>
          )}
          <Section title="All Skills">
            <div className="flex flex-wrap gap-1.5">
              {skills.length > 0
                ? skills.map((s) => <Tag key={s} label={s} />)
                : <p className="text-sm text-gray-400">No skills extracted</p>}
            </div>
          </Section>
        </div>
      )}

      {/* ── Experience ───────────────────────────────────────────── */}
      {activeTab === "experience" && (
        <div className="space-y-6">
          <Section title="💼 Work Experience">
            {typeof experience === "object" && Array.isArray(experience.roles) && experience.roles.length > 0 ? (
              <div className="space-y-4">
                {experience.roles.map((role, i) => (
                  <div key={i} className="border-l-2 border-blue-200 pl-4">
                    <p className="font-semibold text-gray-900">{role.title}</p>
                    {role.company && <p className="text-sm text-gray-600">{role.company}</p>}
                    {role.years && <p className="text-xs text-gray-400">{role.years} years</p>}
                    {role.description && <p className="text-sm text-gray-600 mt-1">{role.description}</p>}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-500">
                Total: {candidate.total_experience_years} years
              </p>
            )}
          </Section>

          <Section title="🔧 Projects">
            {projects.length > 0 ? (
              <div className="space-y-4">
                {projects.map((proj, i) => (
                  <div key={i} className="border border-gray-100 rounded-xl p-4">
                    <p className="font-semibold text-gray-900">{proj.name || `Project ${i + 1}`}</p>
                    {proj.description && (
                      <p className="text-sm text-gray-600 mt-1">{proj.description}</p>
                    )}
                    {Array.isArray(proj.tech_stack) && proj.tech_stack.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {proj.tech_stack.map((t) => <Tag key={t} label={t} color="gray" />)}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : <p className="text-sm text-gray-400">No projects extracted</p>}
          </Section>
        </div>
      )}

      {/* ── Comparison ───────────────────────────────────────────── */}
      {activeTab === "comparison" && (
        <div>
          {!selectedJobId ? (
            <div className="card text-center py-12 text-gray-400">
              Select a job above to see the comparison
            </div>
          ) : !comparison ? (
            <div className="card text-center py-12 text-gray-400">Loading comparison...</div>
          ) : (
            <div className="grid grid-cols-2 gap-6">
              <Section title="✅ Matching Skills">
                <div className="flex flex-wrap gap-1.5">
                  {comparison.comparison?.matching_skills?.length > 0
                    ? comparison.comparison.matching_skills.map((s) => <Tag key={s} label={s} color="green" />)
                    : <p className="text-sm text-gray-400">No matches found</p>}
                </div>
              </Section>
              <Section title="❌ Missing Skills">
                <div className="flex flex-wrap gap-1.5">
                  {comparison.comparison?.missing_skills?.length > 0
                    ? comparison.comparison.missing_skills.map((s) => <Tag key={s} label={s} color="red" />)
                    : <p className="text-sm text-green-600 font-medium">All required skills met!</p>}
                </div>
              </Section>
              <Section title="➕ Additional Skills">
                <div className="flex flex-wrap gap-1.5">
                  {comparison.comparison?.extra_skills?.slice(0, 15).map((s) => (
                    <Tag key={s} label={s} color="gray" />
                  ))}
                </div>
              </Section>
              {comparison.ranking?.total_score != null && (
                <Section title="📊 Score Breakdown">
                  <ScoreBreakdown result={comparison.ranking} />
                </Section>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Feedback ─────────────────────────────────────────────── */}
      {activeTab === "feedback" && (
        <Section title="📝 Recruiter Feedback">
          {feedbackSent ? (
            <div className="text-center py-8">
              <div className="text-4xl mb-3">✅</div>
              <p className="text-gray-700 font-medium">Feedback submitted!</p>
              <p className="text-gray-400 text-sm mt-1">This helps improve future rankings.</p>
              <button
                onClick={() => setFeedbackSent(false)}
                className="btn-secondary text-sm py-1.5 mt-4"
              >
                Update Feedback
              </button>
            </div>
          ) : (
            <div className="space-y-4 max-w-md">
              {!selectedJobId && (
                <p className="text-sm text-amber-600 bg-amber-50 p-3 rounded-lg">
                  Select a job above to submit feedback
                </p>
              )}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Decision</label>
                <select
                  value={feedback.action}
                  onChange={(e) => setFeedback((f) => ({ ...f, action: e.target.value }))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Select action...</option>
                  <option value="shortlisted">Shortlisted</option>
                  <option value="interview">Called for Interview</option>
                  <option value="hired">Hired</option>
                  <option value="rejected">Rejected</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Notes (optional)</label>
                <textarea
                  value={feedback.notes}
                  onChange={(e) => setFeedback((f) => ({ ...f, notes: e.target.value }))}
                  rows={3}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                  placeholder="Additional notes for this candidate..."
                />
              </div>
              <button
                onClick={handleFeedback}
                disabled={!feedback.action || !selectedJobId}
                className="btn-primary"
              >
                Submit Feedback
              </button>
            </div>
          )}
        </Section>
      )}
    </div>
  );
}
