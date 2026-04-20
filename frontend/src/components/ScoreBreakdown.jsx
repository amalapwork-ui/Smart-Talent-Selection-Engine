import React from "react";

const SCORE_COLORS = {
  high: "bg-green-500",
  medium: "bg-yellow-500",
  low: "bg-red-500",
};

function getColor(score) {
  if (score >= 70) return SCORE_COLORS.high;
  if (score >= 45) return SCORE_COLORS.medium;
  return SCORE_COLORS.low;
}

function ScoreBar({ label, score, weight }) {
  const s = score ?? 0;
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="text-gray-600 font-medium">{label}</span>
        <span className="text-gray-900 font-semibold">
          {s.toFixed(1)}
          <span className="text-gray-400 text-xs ml-1">× {weight}</span>
        </span>
      </div>
      <div className="score-bar">
        <div
          className={`score-fill ${getColor(s)}`}
          style={{ width: `${s}%` }}
        />
      </div>
    </div>
  );
}

export default function ScoreBreakdown({ result }) {
  if (!result) return null;

  const components = [
    { label: "Skill Match",        score: result.skill_score,       weight: "40%" },
    { label: "Experience Depth",   score: result.experience_score,   weight: "30%" },
    { label: "Project Relevance",  score: result.project_score,      weight: "20%" },
    { label: "Education & Certs",  score: result.education_score,    weight: "10%" },
  ];

  // vs-jd endpoint stores detail in "breakdown"; RankingResult uses "score_breakdown"
  const breakdown = result.score_breakdown || result.breakdown || {};

  return (
    <div className="space-y-4">
      {/* Total score */}
      <div className="flex items-center gap-4 p-4 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl">
        <div className="text-center">
          <div className="text-3xl font-bold text-blue-700">
            {result.total_score?.toFixed(1)}
          </div>
          <div className="text-xs text-blue-500 font-medium">/ 100</div>
        </div>
        <div className="flex-1">
          <div className="score-bar h-3">
            <div
              className={`score-fill h-3 ${getColor(result.total_score)}`}
              style={{ width: `${result.total_score}%` }}
            />
          </div>
          <p className="text-xs text-gray-500 mt-1">Overall Compatibility Score</p>
        </div>
      </div>

      {/* Component bars */}
      <div className="space-y-3">
        {components.map((c) => (
          <ScoreBar key={c.label} {...c} />
        ))}
      </div>

      {/* Skill details */}
      {breakdown.skill && (
        <div className="border-t pt-4 space-y-3">
          <h4 className="text-sm font-semibold text-gray-700">Skill Analysis</h4>
          {breakdown.skill.matched?.length > 0 && (
            <div>
              <p className="text-xs text-gray-500 mb-1">Matched Skills</p>
              <div className="flex flex-wrap gap-1">
                {breakdown.skill.matched.map((s) => (
                  <span key={s} className="badge bg-green-100 text-green-800">{s}</span>
                ))}
              </div>
            </div>
          )}
          {breakdown.skill.missing?.length > 0 && (
            <div>
              <p className="text-xs text-gray-500 mb-1">Missing Skills</p>
              <div className="flex flex-wrap gap-1">
                {breakdown.skill.missing.map((s) => (
                  <span key={s} className="badge bg-red-100 text-red-700">{s}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Justification */}
      {result.justification && (
        <div className="border-t pt-4">
          <h4 className="text-sm font-semibold text-gray-700 mb-2">AI Justification</h4>
          <p className="text-sm text-gray-600 leading-relaxed bg-gray-50 p-3 rounded-lg italic">
            "{result.justification}"
          </p>
        </div>
      )}
    </div>
  );
}
