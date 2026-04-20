import React from "react";
import { useNavigate } from "react-router-dom";

function ScoreBadge({ score }) {
  const color =
    score >= 70 ? "bg-green-100 text-green-800" :
    score >= 50 ? "bg-yellow-100 text-yellow-800" :
    "bg-red-100 text-red-700";
  return (
    <span className={`badge ${color} text-sm font-bold px-3 py-1`}>
      {score.toFixed(1)}%
    </span>
  );
}

export default function CandidateCard({ result, rank, jobId, onDelete }) {
  const navigate = useNavigate();

  const handleDelete = (e) => {
    e.stopPropagation();
    if (window.confirm(`Remove ${result.candidate_name || "this candidate"} from results? This cannot be undone.`)) {
      onDelete?.(result.candidate_id);
    }
  };

  const candidateName = result.candidate_name || ("Candidate #" + result.candidate_id);

  return (
    <div
      onClick={() => navigate("/candidates/" + result.candidate_id + (jobId ? "?job_id=" + jobId : ""))}
      className="card hover:shadow-md cursor-pointer transition-shadow group"
    >
      <div className="flex items-start gap-4">
        {/* Rank badge */}
        <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm flex-shrink-0 ${
          rank === 1 ? "bg-yellow-100 text-yellow-700" :
          rank === 2 ? "bg-gray-100 text-gray-600" :
          rank === 3 ? "bg-orange-100 text-orange-700" :
          "bg-blue-50 text-blue-600"
        }`}>
          #{rank}
        </div>

        {/* Candidate info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2 mb-1">
            <div className="flex-1 min-w-0">
              <h3 className="font-semibold text-gray-900 truncate group-hover:text-blue-700">
                {candidateName}
              </h3>
              {result.candidate_experience_years > 0 && (
                <p className="text-xs text-gray-400">{result.candidate_experience_years} yrs experience</p>
              )}
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              <ScoreBadge score={result.total_score} />
              {onDelete && (
                <button
                  onClick={handleDelete}
                  title="Remove candidate"
                  className="opacity-0 group-hover:opacity-100 transition-opacity text-gray-300 hover:text-red-500 p-1 rounded"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              )}
            </div>
          </div>

          <p className="text-xs text-gray-400 mb-3 truncate">{result.resume_filename}</p>

          {/* Score mini bars */}
          <div className="grid grid-cols-4 gap-2 mb-3">
            {[
              { label: "Skills",  val: result.skill_score,      color: "bg-blue-500" },
              { label: "Exp.",    val: result.experience_score,  color: "bg-purple-500" },
              { label: "Proj.",   val: result.project_score,     color: "bg-teal-500" },
              { label: "Edu.",    val: result.education_score,   color: "bg-orange-400" },
            ].map(({ label, val, color }) => (
              <div key={label}>
                <div className="text-xs text-gray-400 text-center mb-0.5">{label}</div>
                <div className="score-bar h-1.5">
                  <div className={`score-fill h-1.5 ${color}`} style={{ width: (val || 0) + "%" }} />
                </div>
                <div className="text-xs text-gray-600 text-center mt-0.5">{(val || 0).toFixed(0)}</div>
              </div>
            ))}
          </div>

          {/* Skill tags */}
          {result.candidate_skills?.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {result.candidate_skills.slice(0, 6).map((s) => (
                <span key={s} className="badge bg-blue-50 text-blue-700">{s}</span>
              ))}
              {result.candidate_skills.length > 6 && (
                <span className="badge bg-gray-100 text-gray-500">
                  +{result.candidate_skills.length - 6} more
                </span>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Justification */}
      {result.justification && (
        <p className="mt-3 text-xs text-gray-500 italic border-t pt-3 line-clamp-2">
          {result.justification}
        </p>
      )}
    </div>
  );
}
