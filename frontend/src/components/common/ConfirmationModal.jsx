import React from "react";
import { AnimatePresence, motion } from "framer-motion";
import { FiAlertTriangle, FiX } from "react-icons/fi";

/**
 * Tailwind-native confirmation modal.
 * Pass isOpen/onClose for programmatic control.
 */
function ConfirmationModal({
  isOpen = false,
  onClose,
  title,
  message,
  onConfirm,
  confirmLabel = "Confirm",
  dangerous = true,
}) {
  return (
    <AnimatePresence>
      {isOpen ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="confirm-modal-title"
        >
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="absolute inset-0 bg-navy-900/40 backdrop-blur-sm"
            onClick={onClose}
            aria-hidden="true"
          />

          {/* Panel */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 8 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
            className="relative w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-card-hover"
          >
            {/* Close */}
            {onClose ? (
              <button
                type="button"
                onClick={onClose}
                aria-label="Close dialog"
                className="absolute right-4 top-4 rounded-lg p-1 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600"
              >
                <FiX size={18} />
              </button>
            ) : null}

            <div className="flex items-start gap-4">
              <span className="mt-0.5 shrink-0 rounded-full bg-red-100 p-2 text-red-600">
                <FiAlertTriangle size={20} />
              </span>
              <div>
                <h2 id="confirm-modal-title" className="text-base font-semibold text-slate-900">
                  {title}
                </h2>
                <p className="mt-1 text-sm text-slate-500">{message}</p>
              </div>
            </div>

            <div className="mt-6 flex justify-end gap-3">
              {onClose ? (
                <button type="button" className="app-button-secondary" onClick={onClose}>
                  Cancel
                </button>
              ) : null}
              <button
                type="button"
                className={dangerous ? "app-button-danger" : "app-button"}
                onClick={() => { onConfirm?.(); onClose?.(); }}
              >
                {confirmLabel}
              </button>
            </div>
          </motion.div>
        </div>
      ) : null}
    </AnimatePresence>
  );
}

export default ConfirmationModal;
