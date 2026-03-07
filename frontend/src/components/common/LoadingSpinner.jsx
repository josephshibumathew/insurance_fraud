import React from "react";

function LoadingSpinner({ text = "Loading...", fullPage = false }) {
  const content = (
    <div className="inline-flex items-center gap-3" role="status" aria-live="polite">
      {/* Spinning ring */}
      <span
        className="inline-block h-4 w-4 rounded-full border-2 border-navy-900/20 border-t-navy-700"
        style={{ animation: "spinRing 0.8s linear infinite" }}
        aria-hidden="true"
      />
      <span className="text-sm font-medium text-slate-600">{text}</span>
    </div>
  );

  if (fullPage) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">{content}</div>
    );
  }
  return content;
}

export default LoadingSpinner;
