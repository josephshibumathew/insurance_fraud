import React from "react";
import { FiChevronLeft, FiChevronRight } from "react-icons/fi";

function Pagination({ page, pageSize, total, onPageChange, onPageSizeChange }) {
  const totalPages = Math.max(1, Math.ceil((total || 0) / pageSize));

  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      <p className="text-sm text-slate-500">
        Page <span className="font-medium text-slate-700">{page}</span> of{" "}
        <span className="font-medium text-slate-700">{totalPages}</span>
        {" "}·{" "}
        <span className="font-medium text-slate-700">{total || 0}</span> items
      </p>

      <div className="flex items-center gap-2">
        <label htmlFor="page-size" className="text-sm text-slate-500">
          Rows:
        </label>
        <select
          id="page-size"
          className="app-input w-20 py-1.5"
          value={pageSize}
          onChange={(e) => onPageSizeChange(Number(e.target.value))}
        >
          {[10, 20, 50].map((size) => (
            <option key={size} value={size}>{size}</option>
          ))}
        </select>

        <button
          className="app-icon-btn"
          onClick={() => onPageChange(Math.max(1, page - 1))}
          disabled={page <= 1}
          aria-label="Previous page"
        >
          <FiChevronLeft size={16} />
        </button>
        <button
          className="app-icon-btn"
          onClick={() => onPageChange(Math.min(totalPages, page + 1))}
          disabled={page >= totalPages}
          aria-label="Next page"
        >
          <FiChevronRight size={16} />
        </button>
      </div>
    </div>
  );
}

export default Pagination;
