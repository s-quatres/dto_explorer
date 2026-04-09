#!/usr/bin/env python3
"""Build a hierarchical structure of the codebase for 3D visualization."""

import os
import subprocess
from collections import defaultdict
from pathlib import Path

# Language detection by extension
LANG_MAP = {
    ".go": "Go",
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".json": "JSON",
    ".md": "Markdown",
    ".sh": "Shell",
    ".bash": "Shell",
    ".dockerfile": "Dockerfile",
    ".mod": "Go Module",
    ".sum": "Go Module",
    ".html": "HTML",
    ".css": "CSS",
    ".proto": "Protobuf",
    ".sql": "SQL",
    ".toml": "TOML",
    ".cfg": "Config",
    ".ini": "Config",
    ".txt": "Text",
    ".makefile": "Makefile",
}

LANG_COLORS = {
    "Go": "#00ADD8",
    "Python": "#3776AB",
    "JavaScript": "#F7DF1E",
    "TypeScript": "#3178C6",
    "YAML": "#CB171E",
    "JSON": "#292929",
    "Markdown": "#083FA1",
    "Shell": "#89E051",
    "Dockerfile": "#384D54",
    "Go Module": "#00ADD8",
    "HTML": "#E34C26",
    "CSS": "#563D7C",
    "Protobuf": "#FFA500",
    "Makefile": "#427819",
    "Config": "#888888",
    "Text": "#AAAAAA",
    "Other": "#CCCCCC",
}

IGNORE_DIRS = {".git", "vendor", "node_modules", ".github", "__pycache__"}


def count_lines(filepath: str) -> int:
    """Count lines in a file, returning 0 on error."""
    try:
        with open(filepath, "r", errors="ignore") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def detect_language(filepath: str) -> str:
    """Detect language from file extension or name."""
    name = os.path.basename(filepath).lower()
    if name == "dockerfile" or name.startswith("dockerfile"):
        return "Dockerfile"
    if name == "makefile":
        return "Makefile"
    ext = os.path.splitext(filepath)[1].lower()
    return LANG_MAP.get(ext, "Other")


def get_recent_change_counts(repo_path: str) -> dict:
    """Get number of commits touching each file in the last 90 days."""
    result = subprocess.run(
        ["git", "-C", repo_path, "log", "--name-only", "--format=", "--since=90 days ago"],
        capture_output=True, text=True, check=True
    )
    counts = defaultdict(int)
    for line in result.stdout.strip().split("\n"):
        line = line.strip()
        if line:
            counts[line] += 1
    return counts


def build_tree(repo_path: str) -> dict:
    """Walk the repo and build a tree structure with metadata."""
    change_counts = get_recent_change_counts(repo_path)
    max_changes = max(change_counts.values()) if change_counts else 1

    nodes = []
    links = []
    node_id = 0
    dir_ids = {}  # path -> node id

    # Root node
    root_id = node_id
    nodes.append({
        "id": root_id,
        "name": "dynatrace-operator",
        "type": "directory",
        "depth": 0,
    })
    dir_ids[""] = root_id
    node_id += 1

    for dirpath, dirnames, filenames in os.walk(repo_path):
        # Filter ignored directories
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]

        rel_dir = os.path.relpath(dirpath, repo_path)
        if rel_dir == ".":
            rel_dir = ""

        # Ensure parent directory node exists
        if rel_dir and rel_dir not in dir_ids:
            dir_ids[rel_dir] = node_id
            nodes.append({
                "id": node_id,
                "name": os.path.basename(rel_dir),
                "path": rel_dir,
                "type": "directory",
                "depth": rel_dir.count(os.sep) + 1,
            })
            # Link to parent
            parent_rel = os.path.dirname(rel_dir)
            if parent_rel == ".":
                parent_rel = ""
            parent_id = dir_ids.get(parent_rel, root_id)
            links.append({"source": parent_id, "target": node_id})
            node_id += 1

        for dirname in sorted(dirnames):
            child_rel = os.path.join(rel_dir, dirname) if rel_dir else dirname
            if child_rel not in dir_ids:
                dir_ids[child_rel] = node_id
                nodes.append({
                    "id": node_id,
                    "name": dirname,
                    "path": child_rel,
                    "type": "directory",
                    "depth": child_rel.count(os.sep) + 1,
                })
                current_dir_id = dir_ids.get(rel_dir, root_id)
                links.append({"source": current_dir_id, "target": node_id})
                node_id += 1

        for filename in sorted(filenames):
            filepath = os.path.join(dirpath, filename)
            rel_path = os.path.join(rel_dir, filename) if rel_dir else filename
            lang = detect_language(filepath)
            loc = count_lines(filepath)
            recent_changes = change_counts.get(rel_path, 0)
            heat = recent_changes / max_changes if max_changes > 0 else 0

            nodes.append({
                "id": node_id,
                "name": filename,
                "path": rel_path,
                "type": "file",
                "language": lang,
                "color": LANG_COLORS.get(lang, LANG_COLORS["Other"]),
                "loc": loc,
                "recent_changes": recent_changes,
                "heat": round(heat, 3),
                "depth": rel_path.count(os.sep) + 1,
            })
            parent_id = dir_ids.get(rel_dir, root_id)
            links.append({"source": parent_id, "target": node_id})
            node_id += 1

    return {"nodes": nodes, "links": links}


def compute_language_stats(nodes: list) -> list:
    """Aggregate LOC by language."""
    stats = defaultdict(lambda: {"files": 0, "loc": 0})
    for node in nodes:
        if node.get("type") == "file":
            lang = node.get("language", "Other")
            stats[lang]["files"] += 1
            stats[lang]["loc"] += node.get("loc", 0)
    return [
        {"language": lang, "color": LANG_COLORS.get(lang, "#CCC"), **data}
        for lang, data in sorted(stats.items(), key=lambda x: x[1]["loc"], reverse=True)
    ]


def analyze_codebase_structure(repo_path: str) -> dict:
    """Main entry point: build tree + language stats."""
    tree = build_tree(repo_path)
    lang_stats = compute_language_stats(tree["nodes"])
    print(f"    {len(tree['nodes'])} nodes, {len(tree['links'])} links, {len(lang_stats)} languages")
    return {
        "tree": tree,
        "language_stats": lang_stats,
    }
