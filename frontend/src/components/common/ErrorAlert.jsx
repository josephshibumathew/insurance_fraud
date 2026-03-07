import React from "react";
import { FiAlertCircle, FiX } from "react-icons/fi";

function ErrorAlert({ message, onClose }) {
  if (!message) return null;
  return (
    <div
      className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800"
      role="alert"
    >
      <FiAlertCircle className="mt-0.5 shrink-0 text-red-500" size={16} />
      <span className="flex-1">{message}</span>
      {onClose ? (
        <button
          type="button"
          aria-label="Close"
          onClick={onClose}
          className="ml-auto shrink-0 rounded-md p-0.5 text-red-400 transition hover:bg-red-100 hover:text-red-600"
        >
          <FiX size={15} />
        </button>
      ) : null}
    </div>
  );
}

export default ErrorAlert;
