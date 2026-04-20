import React, { useState } from "react";
import { jobApi } from "../services/api";

const EMPTY_FORM = {
  title: "",
  description: "",
  department: "",
  location: "",
  employment_type: "full_time",
  min_experience_years: 0,
  education_required: "",
  required_skills: "",
  preferred_skills: "",
};

export default function JobForm({ onSuccess, onCancel, initial }) {
  const [form, setForm] = useState(initial ? {
    ...EMPTY_FORM,
    ...initial,
    required_skills: (initial.required_skills || []).join(", "),
    preferred_skills: (initial.preferred_skills || []).join(", "),
  } : EMPTY_FORM);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((f) => ({ ...f, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const payload = {
        ...form,
        min_experience_years: parseInt(form.min_experience_years) || 0,
        required_skills: form.required_skills
          ? form.required_skills.split(",").map((s) => s.trim().toLowerCase()).filter(Boolean)
          : [],
        preferred_skills: form.preferred_skills
          ? form.preferred_skills.split(",").map((s) => s.trim().toLowerCase()).filter(Boolean)
          : [],
      };
      if (initial?.id) {
        await jobApi.update(initial.id, payload);
      } else {
        await jobApi.create(payload);
      }
      onSuccess?.();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to save job. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
          {error}
        </div>
      )}

      <div className="grid grid-cols-2 gap-4">
        <div className="col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-1">Job Title *</label>
          <input
            name="title" value={form.title} onChange={handleChange} required
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="e.g. Senior React Developer"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Department</label>
          <input
            name="department" value={form.department} onChange={handleChange}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Engineering"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Location</label>
          <input
            name="location" value={form.location} onChange={handleChange}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Remote / Bangalore"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Employment Type</label>
          <select
            name="employment_type" value={form.employment_type} onChange={handleChange}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="full_time">Full Time</option>
            <option value="part_time">Part Time</option>
            <option value="contract">Contract</option>
            <option value="internship">Internship</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Min. Experience (years)</label>
          <input
            type="number" min="0" name="min_experience_years"
            value={form.min_experience_years} onChange={handleChange}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div className="col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-1">Education Required</label>
          <input
            name="education_required" value={form.education_required} onChange={handleChange}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="B.Tech or equivalent"
          />
        </div>
        <div className="col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-1">Required Skills (comma-separated)</label>
          <input
            name="required_skills" value={form.required_skills} onChange={handleChange}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="python, django, react, sql"
          />
        </div>
        <div className="col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-1">Preferred Skills (comma-separated)</label>
          <input
            name="preferred_skills" value={form.preferred_skills} onChange={handleChange}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="docker, kubernetes, aws"
          />
        </div>
        <div className="col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-1">Job Description *</label>
          <textarea
            name="description" value={form.description} onChange={handleChange} required rows={6}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
            placeholder="Describe responsibilities, requirements, and expectations..."
          />
        </div>
      </div>

      <div className="flex gap-3 justify-end pt-2">
        <button type="button" onClick={onCancel} className="btn-secondary">
          Cancel
        </button>
        <button type="submit" disabled={loading} className="btn-primary min-w-[120px]">
          {loading ? "Saving..." : initial?.id ? "Update Job" : "Create Job"}
        </button>
      </div>
    </form>
  );
}
