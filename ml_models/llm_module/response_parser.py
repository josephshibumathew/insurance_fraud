"""Parsers and formatters for LLM-generated insurance reports."""

from __future__ import annotations

import re
from dataclasses import dataclass


SECTION_ORDER = [
	"Executive Summary",
	"Evidence Review",
	"SHAP Insights",
	"Recommendation",
	"Next Steps",
	"Disclaimer",
]


@dataclass(slots=True)
class ParsedReport:
	sections: dict[str, str]
	recommendation_points: list[str]


def _normalize_heading(heading: str) -> str:
	heading = heading.strip().strip(":").strip()
	for canonical in SECTION_ORDER:
		if heading.lower() == canonical.lower():
			return canonical
	return heading


def parse_report_sections(text: str) -> dict[str, str]:
	"""Parse markdown-like heading sections into a dictionary."""
	sections: dict[str, list[str]] = {}
	current = "Executive Summary"
	sections[current] = []

	for raw_line in text.splitlines():
		line = raw_line.strip()
		header_match = re.match(r"^(?:#{1,3}\s*)?([A-Za-z][A-Za-z\s]+):?$", line)
		if header_match and _normalize_heading(header_match.group(1)) in SECTION_ORDER:
			current = _normalize_heading(header_match.group(1))
			sections.setdefault(current, [])
			continue
		sections.setdefault(current, []).append(raw_line)

	return {key: "\n".join(value).strip() for key, value in sections.items() if "\n".join(value).strip()}


def extract_recommendations(text: str) -> list[str]:
	"""Extract recommendation bullets from the Recommendation section."""
	sections = parse_report_sections(text)
	recommendation = sections.get("Recommendation", "")
	points: list[str] = []
	for line in recommendation.splitlines():
		stripped = line.strip()
		if stripped.startswith("-"):
			points.append(stripped[1:].strip())
		elif stripped and not points:
			points.append(stripped)
	return points


def format_for_consistent_display(text: str) -> str:
	"""Reformat response text to a consistent section layout."""
	sections = parse_report_sections(text)
	blocks: list[str] = []
	for name in SECTION_ORDER:
		body = sections.get(name, "")
		if body:
			blocks.append(f"{name}:\n{body}")
	if not blocks:
		return text.strip()
	return "\n\n".join(blocks).strip()


def parse_response(text: str) -> ParsedReport:
	"""Parse full response and extract sectioned structure + recommendations."""
	sections = parse_report_sections(text)
	return ParsedReport(sections=sections, recommendation_points=extract_recommendations(text))

