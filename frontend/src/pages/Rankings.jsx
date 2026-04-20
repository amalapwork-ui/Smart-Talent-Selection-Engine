import React, { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { rankingApi, jobApi, candidateApi } from "../services/api";
import CandidateCard from "../components/CandidateCard";

// Multi-skill chip input — press Enter or comma to add a skill tag
function SkillChips({ skills, onChange }) {
  const [input, setInput] = useState("");

  const addSkill = (raw) => {
    const t = raw.trim().toLowerCase();
    if (t && !skills.includes(t)) onChange([...skills, t]);
    setInput("");
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      addSkill(input);
    } else if (e.key === "Backspace" && input === "" && skills.length > 0) {
      onChange(skills.slice(0, -1));
    }
  };

  return (
    <div className="flex flex-wrap items-center gap-1.5 min-h-[38px] w-full border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus-within:ring-2 focus-within:ring-blue-500 bg-white cursor-text">
      {skills.map((s) => (
        <span key={s} className="flex items-center gap-1 bg-blue-100 text-blue-800 px-2 py-0.5 rounded-full text-xs font-medium">
          {s}
          <button
            type="button"
            onClick={() => onChange(skills.filter((x) => x !== s))}
            className="text-blue-500 hover:text-blue-800 leading-none ml-0.5 font-bold"
          >
            &times;
          </button>
        </span>
      ))}
      <input
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={() => { if (input.trim()) addSkill(input); }}
        placeholder={skills.length === 0 ? "python, react... (Enter to add)" : "add more..."}
        className="flex-1 min-w-[120px] outline-none text-sm placeholder-gray-400 bg-transparent"
      />
    </div>
  );
}

export default function Rankings() {
  const { jobId } = useParams();
  const navigate = useNavigate();
  const [jobs, setJobs] = useState([]);
  const [selectedJobId, setSelectedJobId] = useState(jobId || "");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [minScore, setMinScore] = useState("");
  const [skillFilters, setSkillFilters] = useState([]);
  const [runningRank, setRunningRank] = useState(false);

  useEffect(() => {
    jobApi.list().then((res) => {
      const j = res.data.results || res.data;
      setJobs(j);
      if (!selectedJobId && j.length > 0) setSelectedJobId(String(j[0].id));
    });
  }, []);

  const loadResults = useCallback(async () => {
    if (!selectedJobId) return;
    setLoading(true);
    try {
      const params = { job_id: selectedJobId };
      if (minScore) params.min_score = minScore;
      if (skillFilters.length > 0) params.skills = skillFilters.join(",");
      const res = await rankingApi.results(params);
      setResults(res.data.results || res.data);
    } catch {
      toast.error("Failed to load rankings.");
    } finally {
      setLoading(false);
    }
  }, [selectedJobId, minScore, skillFilters]);

  useEffect(() => { loadResults(); }, [loadResults]);
  useEffect(() => { if (jobId) setSelectedJobId(jobId); }, [jobId]);

  const handleRunRanking = async () => {
    if (!selectedJobId) return;
    setRunningRank(true);
    const tid = toast.loading("Starting ranking job...");
    try {
      await jobApi.runRanking(selectedJobId);
      toast.success("Ranking started! Results will refresh shortly.", { id: tid });
      setTimeout(() => { loadResults(); setRunningRank(false); }, 3000);
    } catch {
      toast.error("Failed to start ranking. Try again.", { id: tid });
      setRunningRank(false);
    }
  };

  const handleDeleteCandidate = async (candidateId) => {
    try {
      await candidateApi.delete(candidateId);
      setResults((prev) => prev.filter((r) => r.candidate_id !== candidateId));
      toast.success("Candidate removed.");
    } catch {
      toast.error("Failed to delete candidate.");
    }
  };

  const selectedJob = jobs.find((j) => String(j.id) === String(selectedJobId));
  const topScore = results.length > 0 ? results[0].total_score : 0;
  const avgScore = results.length > 0
    ? results.reduce((a, b) => a + b.total_score, 0) / results.length : 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Candidate Rankings</h1>
        <p className="text-gray-500 text-sm mt-1">AI-ranked candidates sorted by compatibility score</p>
      </div>

      {/* Filters card */}
      <div className="card">
        <div className="flex flex-wrap items-end gap-4">
          <div className="flex-1 min-w-[180px]">
            <label className="block text-xs font-medium text-gray-600 mb-1">Job</label>
            <select
              value={selectedJobId}
              onChange={(e) => { setSelectedJobId(e.target.value); navigate("/rankings/" + e.target.value); }}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Choose a job...</option>
              {jobs.map((j) => <option key={j.id} value={j.id}>{j.title}</option>)}
            </select>
          </div>

          <div className="w-32">
            <label className="block text-xs font-medium text-gray-600 mb-1">Min Score</label>
            <input
              type="number" min="0" max="100" value={minScore}
              onChange={(e) => setMinScore(e.target.value)} placeholder="0"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="flex-1 min-w-[220px]">
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Filter by Skills{" "}
              <span className="text-gray-400 font-normal">(AND logic &mdash; Enter to add)</span>
            </label>
            <SkillChips skills={skillFilters} onChange={setSkillFilters} />
          </div>

          <button
            onClick={handleRunRanking}
            disabled={!selectedJobId || runningRank}
            className="btn-primary self-end whitespace-nowrap"
          >
            {runningRank ? "Running..." : "Run Ranking"}
          </button>
        </div>

        {skillFilters.length > 0 && (
          <p className="text-xs text-gray-400 mt-3">
            Showing candidates with <strong>all of:</strong>{" "}
            {skillFilters.map((s) => (
              <code key={s} className="mx-0.5 bg-gray-100 px-1 rounded">{s}</code>
            ))}
            <button
              onClick={() => setSkillFilters([])}
              className="ml-2 text-red-400 hover:text-red-600 underline"
            >
              clear
            </button>
          </p>
        )}
      </div>

      {/* Stats strip */}
      {results.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {[
            { label: "Total Candidates",     value: results.length },
            { label: "Top Score",            value: topScore.toFixed(1) + "%" },
            { label: "Average Score",        value: avgScore.toFixed(1) + "%" },
            { label: "Strong Matches (>=70)", value: results.filter((r) => r.total_score >= 70).length },
          ].map(({ label, value }) => (
            <div key={label} className="card text-center py-4">
              <p className="text-xl font-bold text-gray-900">{value}</p>
              <p className="text-xs text-gray-500">{label}</p>
            </div>
          ))}
        </div>
      )}

      {/* Results area */}
      {!selectedJobId ? (
        <div className="text-center py-16 text-gray-400">
          <div className="text-4xl mb-3">🎯</div>
          <p>Select a job to view rankings</p>
        </div>
      ) : loading ? (
        <div className="text-center py-16">
          <div className="inline-block w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mb-4" />
          <p className="text-gray-400">Loading rankings...</p>
        </div>
      ) : results.length === 0 ? (
        <div className="card text-center py-16">
          <div className="text-5xl mb-4">🏆</div>
          <h3 className="text-lg font-semibold text-gray-700 mb-2">No rankings yet</h3>
          <p className="text-gray-400 text-sm mb-4">
            {skillFilters.length > 0
              ? "No candidates match all selected skills. Try removing some filters."
              : "Upload resumes and click \"Run Ranking\" to generate scores."}
          </p>
          <div className="flex gap-3 justify-center flex-wrap">
            {skillFilters.length > 0 && (
              <button onClick={() => setSkillFilters([])} className="btn-secondary">Clear Filters</button>
            )}
            <button onClick={() => navigate("/upload")} className="btn-secondary">Upload Resumes</button>
            <button onClick={handleRunRanking} disabled={runningRank} className="btn-primary">Run Ranking</button>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <h2 className="text-base font-semibold text-gray-700">
              {results.length} candidates ranked
              {selectedJob && (
                <span className="text-gray-400 font-normal ml-2">for {selectedJob.title}</span>
              )}
            </h2>
            <div className="flex gap-2 flex-wrap">
              <span className="badge bg-green-100 text-green-700">
                Strong: {results.filter((r) => r.total_score >= 70).length}
              </span>
              <span className="badge bg-yellow-100 text-yellow-700">
                Moderate: {results.filter((r) => r.total_score >= 50 && r.total_score < 70).length}
              </span>
              <span className="badge bg-red-100 text-red-700">
                Weak: {results.filter((r) => r.total_score < 50).length}
              </span>
            </div>
          </div>
          <div className="grid grid-cols-1 gap-4">
            {results.map((result, i) => (
              <CandidateCard
                key={result.id}
                result={result}
                rank={i + 1}
                jobId={selectedJobId}
                onDelete={handleDeleteCandidate}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
