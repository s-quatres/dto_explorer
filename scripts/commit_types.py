#!/usr/bin/env python3
"""Classify commits by type (feature, bugfix, refactor, etc.) and aggregate."""

import re
import subprocess
from collections import defaultdict
from datetime import datetime

# Conventional commit pattern
CONVENTIONAL_RE = re.compile(
    r"^(feat|fix|docs|style|refactor|perf|test|chore|ci|revert|build|release)(\(.+?\))?[!]?:"
)

# Keyword-based fallback classification
KEYWORD_RULES = [
    ("bugfix", ["fix", "bug", "issue", "resolve", "patch", "hotfix", "crash", "error"]),
    ("feature", ["add", "implement", "feature", "new", "introduce", "support", "enable"]),
    ("refactor", ["refactor", "cleanup", "clean up", "reorganize", "rename", "restructure", "simplify", "move"]),
    ("docs", ["doc", "readme", "comment", "changelog", "license"]),
    ("test", ["test", "spec", "coverage", "e2e", "integration test", "unit test"]),
    ("ci", ["ci", "pipeline", "workflow", "github action", "jenkins", "travis"]),
    ("deps", ["bump", "upgrade", "dependency", "dependabot", "renovate", "go.mod", "go.sum"]),
    ("chore", ["chore", "lint", "format", "config", "setup", "release", "version"]),
    ("perf", ["perf", "optimize", "performance", "faster", "speed", "cache"]),
]

# Bot authors
BOT_AUTHORS = {"renovate[bot]", "dependabot[bot]", "renovate", "dependabot"}

# Map conventional types to our display categories
TYPE_MAP = {
    "feat": "feature",
    "fix": "bugfix",
    "docs": "docs",
    "style": "chore",
    "refactor": "refactor",
    "perf": "perf",
    "test": "test",
    "chore": "chore",
    "ci": "ci",
    "revert": "other",
    "build": "chore",
    "release": "chore",
}

CATEGORY_COLORS = {
    "feature": "#4CAF50",
    "bugfix": "#F44336",
    "refactor": "#FF9800",
    "docs": "#2196F3",
    "test": "#9C27B0",
    "ci": "#00BCD4",
    "deps": "#795548",
    "chore": "#607D8B",
    "perf": "#FFEB3B",
    "other": "#9E9E9E",
}


def classify_commit(message: str, author: str) -> str:
    """Classify a single commit message into a category."""
    msg_lower = message.lower().strip()

    # Merge commits
    if msg_lower.startswith("merge"):
        return "other"

    # Bot authors → deps
    if author.lower() in BOT_AUTHORS:
        return "deps"

    # Conventional commits
    match = CONVENTIONAL_RE.match(message)
    if match:
        conv_type = match.group(1)
        return TYPE_MAP.get(conv_type, "other")

    # Keyword fallback
    for category, keywords in KEYWORD_RULES:
        if any(kw in msg_lower for kw in keywords):
            return category

    return "other"


def get_commits(repo_path: str) -> list:
    """Extract all commits with hash, date, author, message."""
    sep = "|||"
    result = subprocess.run(
        ["git", "-C", repo_path, "log", "--all", f"--format=%H{sep}%aI{sep}%an{sep}%s"],
        capture_output=True, text=True, check=True
    )
    commits = []
    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split(sep, 3)
        if len(parts) != 4:
            continue
        commits.append({
            "hash": parts[0],
            "date": parts[1],
            "author": parts[2],
            "message": parts[3],
        })
    return commits


def analyze_commit_types(repo_path: str) -> dict:
    """Classify all commits and produce aggregated statistics."""
    commits = get_commits(repo_path)
    print(f"    Total commits: {len(commits)}")

    # Classify each commit
    classified = []
    type_counts = defaultdict(int)
    monthly_counts = defaultdict(lambda: defaultdict(int))
    author_type_counts = defaultdict(lambda: defaultdict(int))
    weekday_counts = defaultdict(int)
    message_lengths = []

    for commit in commits:
        cat = classify_commit(commit["message"], commit["author"])
        type_counts[cat] += 1

        # Parse date for monthly aggregation
        try:
            dt = datetime.fromisoformat(commit["date"])
            month_key = dt.strftime("%Y-%m")
            monthly_counts[month_key][cat] += 1
            weekday_counts[dt.strftime("%A")] += 1
        except ValueError:
            pass

        author_type_counts[commit["author"]][cat] += 1
        message_lengths.append(len(commit["message"]))

    # Build type distribution
    distribution = [
        {"type": t, "count": c, "color": CATEGORY_COLORS.get(t, "#999")}
        for t, c in sorted(type_counts.items(), key=lambda x: x[1], reverse=True)
    ]

    # Build monthly timeline (sorted by month)
    categories = sorted(type_counts.keys())
    timeline = []
    for month in sorted(monthly_counts.keys()):
        entry = {"month": month}
        for cat in categories:
            entry[cat] = monthly_counts[month].get(cat, 0)
        timeline.append(entry)

    # Top authors by total commits, with breakdown
    author_totals = {
        author: sum(cats.values())
        for author, cats in author_type_counts.items()
    }
    top_authors = sorted(author_totals.items(), key=lambda x: x[1], reverse=True)[:15]
    authors = [
        {
            "author": author,
            "total": total,
            "breakdown": dict(author_type_counts[author]),
        }
        for author, total in top_authors
    ]

    # Fun stats
    weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    busiest_day = max(weekday_counts.items(), key=lambda x: x[1])[0] if weekday_counts else "N/A"
    avg_msg_len = round(sum(message_lengths) / len(message_lengths), 1) if message_lengths else 0

    fun_stats = {
        "total_commits": len(commits),
        "busiest_weekday": busiest_day,
        "avg_message_length": avg_msg_len,
        "weekday_distribution": {d: weekday_counts.get(d, 0) for d in weekday_order},
        "unique_authors": len(author_type_counts),
        "first_commit_date": commits[-1]["date"] if commits else None,
        "latest_commit_date": commits[0]["date"] if commits else None,
    }

    print(f"    Categories: {dict(type_counts)}")

    return {
        "distribution": distribution,
        "timeline": timeline,
        "categories": categories,
        "authors": authors,
        "fun_stats": fun_stats,
    }
