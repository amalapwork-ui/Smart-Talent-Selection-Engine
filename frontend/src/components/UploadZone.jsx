import React, { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";

const ACCEPTED = {
  "application/pdf": [".pdf"],
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
  "image/jpeg": [".jpg", ".jpeg"],
  "image/png": [".png"],
};

export default function UploadZone({ onFilesSelected }) {
  const [dragOver, setDragOver] = useState(false);

  const onDrop = useCallback(
    (accepted, rejected) => {
      setDragOver(false);
      if (rejected.length > 0) {
        alert(
          `${rejected.length} file(s) rejected. Only PDF, DOCX, JPG, PNG are allowed (max 10 MB each).`
        );
      }
      if (accepted.length > 0) {
        onFilesSelected(accepted);
      }
    },
    [onFilesSelected]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    onDragEnter: () => setDragOver(true),
    onDragLeave: () => setDragOver(false),
    accept: ACCEPTED,
    maxSize: 10 * 1024 * 1024,
    multiple: true,
  });

  return (
    <div
      {...getRootProps()}
      className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all
        ${isDragActive || dragOver
          ? "border-blue-500 bg-blue-50"
          : "border-gray-300 bg-white hover:border-blue-400 hover:bg-gray-50"}`}
    >
      <input {...getInputProps()} />
      <div className="text-5xl mb-4">{isDragActive ? "📂" : "📁"}</div>
      <p className="text-lg font-semibold text-gray-700 mb-2">
        {isDragActive ? "Drop resumes here..." : "Drag & drop resumes here"}
      </p>
      <p className="text-sm text-gray-500 mb-4">or click to browse files</p>
      <div className="flex justify-center gap-2 flex-wrap">
        {["PDF", "DOCX", "JPG", "PNG"].map((f) => (
          <span key={f} className="badge bg-gray-100 text-gray-600 text-xs">
            {f}
          </span>
        ))}
      </div>
      <p className="text-xs text-gray-400 mt-2">Max 10 MB per file • Bulk upload supported</p>
    </div>
  );
}
