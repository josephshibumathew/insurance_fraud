"""Log file reader for admin endpoints."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path


class LogService:
    def __init__(self, log_file_path: str) -> None:
        self.log_file_path = Path(log_file_path)

    def tail(self, lines: int = 200) -> list[str]:
        if lines <= 0:
            return []
        if not self.log_file_path.exists():
            return []

        with self.log_file_path.open("r", encoding="utf-8", errors="ignore") as file_obj:
            all_lines = file_obj.readlines()
        return [line.rstrip("\n") for line in all_lines[-lines:]]

    @staticmethod
    def tail_file(path: str | Path, lines: int = 200) -> list[str]:
        file_path = Path(path)
        if lines <= 0 or not file_path.exists():
            return []

        with file_path.open("r", encoding="utf-8", errors="ignore") as file_obj:
            all_lines = file_obj.readlines()
        return [line.rstrip("\n") for line in all_lines[-lines:]]

    @staticmethod
    def collect_named_logs(log_map: Mapping[str, str | Path], lines: int = 200) -> dict[str, object]:
        logs: dict[str, object] = {}
        for name, path in log_map.items():
            file_path = Path(path)
            logs[name] = {
                "file": str(file_path),
                "lines": LogService.tail_file(file_path, lines=lines),
            }
        return logs
