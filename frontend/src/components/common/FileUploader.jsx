import React, { useRef, useState } from "react";
import { FiUploadCloud } from "react-icons/fi";

function FileUploader({ accept = "*", multiple = false, onFilesSelected, label = "Upload files" }) {
  const inputRef = useRef(null);
  const [dragActive, setDragActive] = useState(false);

  const handleFiles = (files) => {
    if (!files || files.length === 0) return;
    onFilesSelected(Array.from(files));
  };

  const onDrop = (event) => {
    event.preventDefault();
    setDragActive(false);
    handleFiles(event.dataTransfer.files);
  };

  return (
    <div
      className={`dropzone ${dragActive ? "active" : ""}`}
      onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
      onDragLeave={() => setDragActive(false)}
      onDrop={onDrop}
      role="button"
      tabIndex={0}
      aria-label="Drag and drop file uploader"
      onClick={() => inputRef.current?.click()}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          inputRef.current?.click();
        }
      }}
    >
      <FiUploadCloud size={28} className="mx-auto mb-2 text-navy-500" />
      <p className="text-sm font-semibold text-slate-700">{label}</p>
      <p className="mt-1 text-xs text-slate-400">Drag and drop or click to browse</p>
      <input
        ref={inputRef}
        type="file"
        className="hidden"
        accept={accept}
        multiple={multiple}
        onChange={(e) => handleFiles(e.target.files)}
      />
    </div>
  );
}

export default FileUploader;
