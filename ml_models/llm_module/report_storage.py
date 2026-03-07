"""Database persistence for generated fraud reports with versioning and export."""

from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from typing import Any

@dataclass(slots=True)
class GeneratedReport:
    id: int
    claim_id: int
    version: int
    risk_level: str
    fraud_score: float
    report_text: str
    parsed_sections: dict[str, Any]
    html_content: str | None
    pdf_path: str | None
    created_at: datetime


class ReportStorage:
    """Store, version, and export generated reports in PostgreSQL."""

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or os.getenv(
            "DATABASE_URL", "sqlite:///generated_reports.db"
        )

    def _connect(self):
        if self.database_url.startswith("postgresql"):
            try:
                import importlib

                psycopg2 = importlib.import_module("psycopg2")
            except Exception as exc:
                raise ImportError("psycopg2 is required for PostgreSQL storage.") from exc

            parsed = urlparse(self.database_url.replace("postgresql+psycopg2", "postgresql"))
            return psycopg2.connect(
                dbname=(parsed.path or "").lstrip("/") or "postgres",
                user=parsed.username,
                password=parsed.password,
                host=parsed.hostname,
                port=parsed.port or 5432,
            ), "postgres"

        sqlite_path = self.database_url.replace("sqlite:///", "")
        conn = sqlite3.connect(sqlite_path)
        conn.row_factory = sqlite3.Row
        return conn, "sqlite"

    @staticmethod
    def _placeholder(db_kind: str) -> str:
        return "%s" if db_kind == "postgres" else "?"

    def initialize(self) -> None:
        conn, db_kind = self._connect()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS claims (
                    id INTEGER PRIMARY KEY,
                    external_claim_id VARCHAR(64),
                    status VARCHAR(32) DEFAULT 'submitted',
                    created_at TIMESTAMP
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS generated_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    claim_id INTEGER NOT NULL,
                    version INTEGER NOT NULL,
                    risk_level VARCHAR(16) NOT NULL,
                    fraud_score FLOAT NOT NULL,
                    report_text TEXT NOT NULL,
                    parsed_sections TEXT,
                    html_content TEXT,
                    pdf_path TEXT,
                    created_at TIMESTAMP,
                    FOREIGN KEY (claim_id) REFERENCES claims(id)
                )
                """
                if db_kind == "sqlite"
                else """
                CREATE TABLE IF NOT EXISTS generated_reports (
                    id SERIAL PRIMARY KEY,
                    claim_id INTEGER NOT NULL REFERENCES claims(id),
                    version INTEGER NOT NULL,
                    risk_level VARCHAR(16) NOT NULL,
                    fraud_score DOUBLE PRECISION NOT NULL,
                    report_text TEXT NOT NULL,
                    parsed_sections JSONB,
                    html_content TEXT,
                    pdf_path TEXT,
                    created_at TIMESTAMP
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _row_to_report(row: Any) -> GeneratedReport:
        is_mapping_row = isinstance(row, (dict, sqlite3.Row))
        created_at = row["created_at"] if is_mapping_row else row[9]
        if isinstance(created_at, str):
            created_at_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        elif isinstance(created_at, datetime):
            created_at_dt = created_at
        else:
            created_at_dt = datetime.now(timezone.utc)
        parsed_sections_raw = row["parsed_sections"] if is_mapping_row else row[6]
        parsed_sections = parsed_sections_raw if isinstance(parsed_sections_raw, dict) else json.loads(parsed_sections_raw or "{}")
        return GeneratedReport(
            id=int(row["id"] if is_mapping_row else row[0]),
            claim_id=int(row["claim_id"] if is_mapping_row else row[1]),
            version=int(row["version"] if is_mapping_row else row[2]),
            risk_level=str(row["risk_level"] if is_mapping_row else row[3]),
            fraud_score=float(row["fraud_score"] if is_mapping_row else row[4]),
            report_text=str(row["report_text"] if is_mapping_row else row[5]),
            parsed_sections=parsed_sections,
            html_content=row["html_content"] if is_mapping_row else row[7],
            pdf_path=row["pdf_path"] if is_mapping_row else row[8],
            created_at=created_at_dt,
        )

    def save_report(
        self,
        *,
        claim_id: int,
        fraud_score: float,
        risk_level: str,
        report_text: str,
        parsed_sections: dict[str, Any],
        html_content: str | None = None,
        pdf_path: str | None = None,
    ) -> GeneratedReport:
        conn, db_kind = self._connect()
        p = self._placeholder(db_kind)
        now_iso = datetime.now(timezone.utc).isoformat()
        try:
            cur = conn.cursor()

            cur.execute(
                f"SELECT 1 FROM claims WHERE id = {p}",
                (claim_id,),
            )
            if not cur.fetchone():
                cur.execute(
                    f"INSERT INTO claims (id, status, created_at) VALUES ({p}, {p}, {p})",
                    (claim_id, "submitted", now_iso),
                )

            cur.execute(
                f"SELECT COALESCE(MAX(version), 0) FROM generated_reports WHERE claim_id = {p}",
                (claim_id,),
            )
            version = int(cur.fetchone()[0]) + 1

            cur.execute(
                f"""
                INSERT INTO generated_reports
                (claim_id, version, risk_level, fraud_score, report_text, parsed_sections, html_content, pdf_path, created_at)
                VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p})
                """,
                (
                    claim_id,
                    version,
                    risk_level,
                    float(fraud_score),
                    report_text,
                    json.dumps(parsed_sections),
                    html_content,
                    pdf_path,
                    now_iso,
                ),
            )

            if db_kind == "postgres":
                cur.execute("SELECT LASTVAL()")
                report_id = int(cur.fetchone()[0])
            else:
                report_id = int(cur.lastrowid or 0)

            conn.commit()
            return GeneratedReport(
                id=report_id,
                claim_id=claim_id,
                version=version,
                risk_level=risk_level,
                fraud_score=float(fraud_score),
                report_text=report_text,
                parsed_sections=parsed_sections,
                html_content=html_content,
                pdf_path=pdf_path,
                created_at=datetime.now(timezone.utc),
            )
        finally:
            conn.close()

    def get_latest_report(self, claim_id: int) -> GeneratedReport | None:
        conn, db_kind = self._connect()
        p = self._placeholder(db_kind)
        try:
            cur = conn.cursor()
            cur.execute(
                f"""
                SELECT id, claim_id, version, risk_level, fraud_score, report_text, parsed_sections, html_content, pdf_path, created_at
                FROM generated_reports
                WHERE claim_id = {p}
                ORDER BY version DESC
                LIMIT 1
                """,
                (claim_id,),
            )
            row = cur.fetchone()
            return None if row is None else self._row_to_report(row)
        finally:
            conn.close()

    def get_report_version(self, claim_id: int, version: int) -> GeneratedReport | None:
        conn, db_kind = self._connect()
        p = self._placeholder(db_kind)
        try:
            cur = conn.cursor()
            cur.execute(
                f"""
                SELECT id, claim_id, version, risk_level, fraud_score, report_text, parsed_sections, html_content, pdf_path, created_at
                FROM generated_reports
                WHERE claim_id = {p} AND version = {p}
                LIMIT 1
                """,
                (claim_id, version),
            )
            row = cur.fetchone()
            return None if row is None else self._row_to_report(row)
        finally:
            conn.close()

    def export_report(self, report: GeneratedReport, fmt: str = "pdf", export_dir: str | Path | None = None) -> Path:
        target_dir = Path(export_dir or "generated_reports")
        target_dir.mkdir(parents=True, exist_ok=True)

        safe_fmt = fmt.lower().strip()
        if safe_fmt not in {"pdf", "html"}:
            raise ValueError("fmt must be 'pdf' or 'html'")

        if safe_fmt == "pdf":
            if not report.pdf_path:
                raise FileNotFoundError("No PDF path stored for this report.")
            source = Path(report.pdf_path)
            if not source.exists():
                raise FileNotFoundError(f"Stored PDF not found: {source}")
            return source

        output = target_dir / f"claim_{report.claim_id}_v{report.version}.html"
        html = report.html_content or f"<html><body><pre>{report.report_text}</pre></body></html>"
        output.write_text(html, encoding="utf-8")
        return output
