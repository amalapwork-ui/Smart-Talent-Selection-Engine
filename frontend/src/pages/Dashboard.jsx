import React, { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { resumeApi, jobApi, rankingApi } from "../services/api";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from "recharts";

const STATUS_COLORS = {
  done: "#22c55e",
  processing: "#f59e0b",
  pending: "#3b82f6",
  error: "#ef4444",
};

function StatCard({ icon, label, value, sub, color = "blue" }) {
  const colors = {
    blue: "bg-blue-50 text-blue-700",
    green: "bg-green-50 text-green-700",
    purple: "bg-purple-50 text-purple-700",
    orange: "bg-orange-50 text-orange-700",
  };
  return (
    <div className="card flex items-center gap-4">
      <div className={`w-12 h-12 rounded-xl flex items-center justify-center text-2xl ${colors[color]}`}>
        {icon}
      </div>
      <div>
        <p className="text-2xl font-bold text-gray-900">{value}</p>
        <p className="text-sm font-medium text-gray-700">{label}</p>
        {sub && <p className="text-xs text-gray-400">{sub}</p>}
      </div>
    </div>
  );
}

export default function Dashboard() {
  const navigate = useNavigate();
  const [resumeStats, setResumeStats] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [topRanked, setTopRanked] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true); else setLoading(true);
    try {
      const [statsRes, jobsRes] = await Promise.all([
        resumeApi.stats(),
        jobApi.list({ is_active: true }),
      ]);
      setResumeStats(statsRes.data);
      setJobs(jobsRes.data.results || jobsRes.data);

      const activeJobs = jobsRes.data.results || jobsRes.data;
      if (activeJobs.length > 0) {
        const rankRes = await rankingApi.results({ job_id: activeJobs[0].id });
        const results = rankRes.data.results || rankRes.data;
        setTopRanked(Array.isArray(results) ? results.slice(0, 5) : []);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="text-4xl mb-4 animate-bounce">⚡</div>
          <p className="text-gray-500">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  const statusData = resumeStats?.by_status
    ? Object.entries(resumeStats.by_status).map(([name, value]) => ({ name, value }))
    : [];

  const roleData = resumeStats?.by_role?.slice(0, 6) || [];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-500 text-sm mt-1">Overview of your hiring pipeline</p>
        </div>
        <button
          onClick={() => load(true)}
          disabled={refreshing}
          className="btn-secondary text-sm py-1.5 flex items-center gap-2"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`}
            fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round"
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          {refreshing ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard icon="📄" label="Total Resumes" value={resumeStats?.total || 0} color="blue" />
        <StatCard
          icon="✅" label="Processed"
          value={resumeStats?.by_status?.done || 0}
          sub={`${resumeStats?.by_status?.error || 0} errors`}
          color="green"
        />
        <StatCard icon="💼" label="Active Jobs" value={jobs.filter((j) => j.is_active).length} color="purple" />
        <StatCard icon="⏳" label="In Queue" value={resumeStats?.by_status?.pending || 0} color="orange" />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-2 gap-6">
        {/* Status distribution */}
        <div className="card">
          <h2 className="text-base font-semibold text-gray-800 mb-4">Resume Status</h2>
          {statusData.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie data={statusData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80}>
                  {statusData.map((entry) => (
                    <Cell key={entry.name} fill={STATUS_COLORS[entry.name] || "#9ca3af"} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-48 flex items-center justify-center text-gray-400 text-sm">
              No data yet — upload some resumes
            </div>
          )}
          <div className="flex justify-center gap-4 mt-2">
            {statusData.map(({ name, value }) => (
              <div key={name} className="flex items-center gap-1.5 text-xs">
                <div className="w-2.5 h-2.5 rounded-full" style={{ background: STATUS_COLORS[name] || "#9ca3af" }} />
                <span className="text-gray-600 capitalize">{name}: {value}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Roles breakdown */}
        <div className="card">
          <h2 className="text-base font-semibold text-gray-800 mb-4">Resumes by Role</h2>
          {roleData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={roleData} layout="vertical" margin={{ left: 20 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 11 }} />
                <YAxis dataKey="job_role" type="category" tick={{ fontSize: 11 }} width={80} />
                <Tooltip />
                <Bar dataKey="count" fill="#3b82f6" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-48 flex items-center justify-center text-gray-400 text-sm">
              No data yet
            </div>
          )}
        </div>
      </div>

      {/* Active jobs + top candidates */}
      <div className="grid grid-cols-2 gap-6">
        {/* Active jobs */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold text-gray-800">Active Jobs</h2>
            <button onClick={() => navigate("/jobs")} className="text-xs text-blue-600 hover:underline">
              View all →
            </button>
          </div>
          {jobs.length === 0 ? (
            <div className="text-center py-8 text-gray-400">
              <div className="text-3xl mb-2">💼</div>
              <p className="text-sm">No jobs created yet</p>
              <button onClick={() => navigate("/jobs")} className="btn-primary mt-3 text-xs py-1.5 px-3">
                + Create Job
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              {jobs.slice(0, 5).map((job) => (
                <div
                  key={job.id}
                  onClick={() => navigate(`/rankings/${job.id}`)}
                  className="flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 cursor-pointer border border-gray-100"
                >
                  <div>
                    <p className="text-sm font-medium text-gray-900">{job.title}</p>
                    <p className="text-xs text-gray-500">{job.department || "General"} • {job.location || "Remote"}</p>
                  </div>
                  <div className="text-right">
                    <span className="badge bg-blue-50 text-blue-700">{job.ranked_count} ranked</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Top candidates */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold text-gray-800">Top Candidates</h2>
            {jobs.length > 0 && (
              <button onClick={() => navigate(`/rankings/${jobs[0]?.id}`)} className="text-xs text-blue-600 hover:underline">
                Full rankings →
              </button>
            )}
          </div>
          {topRanked.length === 0 ? (
            <div className="text-center py-8 text-gray-400">
              <div className="text-3xl mb-2">🏆</div>
              <p className="text-sm">Run ranking to see top candidates</p>
            </div>
          ) : (
            <div className="space-y-3">
              {topRanked.map((r, i) => (
                <div
                  key={r.id}
                  onClick={() => navigate(`/candidates/${r.candidate_id}`)}
                  className="flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50 cursor-pointer border border-gray-100"
                >
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${
                    i === 0 ? "bg-yellow-100 text-yellow-700" :
                    i === 1 ? "bg-gray-100 text-gray-600" :
                    i === 2 ? "bg-orange-100 text-orange-700" :
                    "bg-blue-50 text-blue-600"
                  }`}>#{i + 1}</div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {r.candidate_name || `Candidate #${r.candidate_id}`}
                    </p>
                    <p className="text-xs text-gray-500">{r.candidate_experience_years}y exp</p>
                  </div>
                  <span className={`badge text-xs font-bold ${
                    r.total_score >= 70 ? "bg-green-100 text-green-800" :
                    r.total_score >= 50 ? "bg-yellow-100 text-yellow-700" :
                    "bg-red-100 text-red-700"
                  }`}>
                    {r.total_score?.toFixed(1)}%
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
