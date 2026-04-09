#!/usr/bin/env python3
"""Analyze most-changed files over different time periods using git log."""

import subprocess
from collections import defaultdict
from datetime import datetime, timedelta, timezone


def git_log_numstat(repo_path: str, since_date: str) -> str:
    """Run git log --numstat and return raw output."""
    result = subprocess.run(
        ["git", "-C", repo_path, "log", "--numstat", "--format=", f"--since={since_date}"],
        capture_output=True, text=True, check=True
    )
    return result.stdout


def parse_numstat(raw: str) -> dict:
    """Parse git numstat output into per-file change counts."""
    files = defaultdict(lambda: {"additions": 0, "deletions": 0, "changes": 0})
    for line in raw.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        added, deleted, filepath = parts
        if added == "-" or deleted == "-":  # binary files
            continue
        added, deleted = int(added), int(deleted)
        files[filepath]["additions"] += added
        files[filepath]["deletions"] += deleted
        files[filepath]["changes"] += added + deleted
    return files


def top_files(files: dict, n: int = 20) -> list:
    """Return top N files sorted by total changes."""
    sorted_files = sorted(files.items(), key=lambda x: x[1]["changes"], reverse=True)
    return [
        {
            "file": filepath,
            "additions": stats["additions"],
            "deletions": stats["deletions"],
            "changes": stats["changes"],
        }
        for filepath, stats in sorted_files[:n]
    ]


def analyze_file_changes(repo_path: str) -> dict:
    """Compute top 20 most-changed files for week, month, year, 5 years."""
    now = datetime.now(timezone.utc)
    periods = {
        "week": (now - timedelta(weeks=1)).strftime("%Y-%m-%d"),
        "month": (now - timedelta(days=30)).strftime("%Y-%m-%d"),
        "year": (now - timedelta(days=365)).strftime("%Y-%m-%d"),
        "five_years": (now - timedelta(days=5 * 365)).strftime("%Y-%m-%d"),
    }

    result = {}
    for period_name, since_date in periods.items():
        print(f"    Scanning {period_name} (since {since_date})...")
        raw = git_log_numstat(repo_path, since_date)
        files = parse_numstat(raw)
        result[period_name] = top_files(files, 20)
        print(f"      Found {len(files)} files with changes, top 20 selected")

    return {"periods": result}
