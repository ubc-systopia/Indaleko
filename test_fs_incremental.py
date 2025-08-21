import os
import time

from datetime import UTC, datetime

from activity.collectors.storage.fs_incremental import FsIncrementalCollector
from activity.recorders.storage.fs_incremental_recorder import FsIncrementalRecorder


def test_incremental_indexer(tmp_path):
    # Setup a temporary directory with files
    base = tmp_path / "data"
    base.mkdir()
    file1 = base / "a.txt"
    file2 = base / "b.txt"
    file1.write_text("hello", encoding="utf-8")
    file2.write_text("world", encoding="utf-8")

    state_file = tmp_path / "state.json"
    output_file = tmp_path / "out.jsonl"

    # First run: full scan, collect both files
    coll1 = FsIncrementalCollector(
        volumes=[str(base)],
        state_file=str(state_file),
        patterns=["*.txt"],
    )
    acts1 = coll1.collect_activities()
    assert len(acts1) == 2

    rec1 = FsIncrementalRecorder(output_file=str(output_file))
    count1 = rec1.store_activities(acts1)
    assert count1 == 2
    # Ensure output lines equal count
    with open(output_file, encoding="utf-8") as f:
        lines = f.read().splitlines()
    assert len(lines) == 2

    # Second run immediately: no new files
    coll2 = FsIncrementalCollector(
        volumes=[str(base)],
        state_file=str(state_file),
        patterns=["*.txt"],
    )
    acts2 = coll2.collect_activities()
    assert len(acts2) == 0

    # Touch file1 to update its mtime
    new_time = datetime.now(UTC).timestamp() + 1
    os.utime(file1, (new_time, new_time))
    # Wait a moment to ensure state change
    time.sleep(0.01)

    # Third run: only file1 should be detected
    coll3 = FsIncrementalCollector(
        volumes=[str(base)],
        state_file=str(state_file),
        patterns=["*.txt"],
    )
    acts3 = coll3.collect_activities()
    paths = [a["file_path"] for a in acts3]
    assert any(p.endswith("a.txt") for p in paths)
    assert len(acts3) == 1
