"""
Incremental file system collector for Indaleko.

This collector walks configured volumes and emits file metadata for files
with modification timestamps newer than a stored "last run" timestamp.
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class FsIncrementalCollector:
    """
    Collector that scans directories incrementally based on file mtime.
    """

    def __init__(
        self,
        volumes: list[str],
        state_file: str = "data/fs_indexer_state.json",
        patterns: list[str] | None = None,
    ):
        self.volumes = volumes
        self.state_path = Path(state_file)
        self.patterns = patterns or ["*"]
        # Load last run timestamp
        if self.state_path.is_file():
            try:
                data = json.loads(self.state_path.read_text(encoding="utf-8"))
                ts = data.get("last_run")
                self.last_run = datetime.fromisoformat(ts) if ts else None
            except Exception:
                self.last_run = None
        else:
            self.last_run = None
        # Current run timestamp to update state
        self.current_run = datetime.now(UTC)

    def collect_activities(self) -> list[dict[str, Any]]:
        """
        Scan volumes and return list of file events newer than last_run.
        """
        activities: list[dict[str, Any]] = []
        for vol in self.volumes:
            base = Path(vol)
            for pattern in self.patterns:
                for p in base.rglob(pattern):
                    if not p.is_file():
                        continue
                    try:
                        mtime = datetime.fromtimestamp(p.stat().st_mtime, UTC)
                    except Exception:
                        continue
                    # If full scan or new/modified
                    if self.last_run is None or mtime >= self.last_run:
                        activities.append(
                            {
                                "file_path": str(p),
                                "modified_time": mtime.isoformat(),
                                "size_bytes": p.stat().st_size,
                            },
                        )
        # Update state file
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(
            json.dumps({"last_run": self.current_run.isoformat()}, indent=2),
            encoding="utf-8",
        )
        return activities
