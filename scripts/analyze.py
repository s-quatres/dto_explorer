#!/usr/bin/env python3
"""Orchestrator: clones dynatrace-operator and runs all analysis modules."""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from file_changes import analyze_file_changes
from codebase_structure import analyze_codebase_structure
from commit_types import analyze_commit_types

REPO_URL = "https://github.com/Dynatrace/dynatrace-operator.git"
CLONE_DIR = "repo_clone"
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", os.path.join(os.path.dirname(__file__), "..", "site", "data"))


def clone_repo(url: str, dest: str) -> str:
    """Clone the repo with full history. If already exists, fetch latest."""
    if os.path.isdir(dest):
        print(f"Repo already exists at {dest}, fetching latest...")
        subprocess.run(["git", "-C", dest, "fetch", "--all"], check=True)
        subprocess.run(["git", "-C", dest, "reset", "--hard", "origin/main"], check=True)
    else:
        print(f"Cloning {url} into {dest} (full history)...")
        subprocess.run(["git", "clone", url, dest], check=True)
    return os.path.abspath(dest)


def write_json(data: dict, filename: str, output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, default=str)
    print(f"  Written: {filepath}")


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    clone_dest = os.path.join(script_dir, "..", CLONE_DIR)
    output_dir = os.path.abspath(OUTPUT_DIR)

    print("=" * 60)
    print("DTO Explorer — Dynatrace Operator Analysis")
    print("=" * 60)

    # Step 1: Clone / update
    repo_path = clone_repo(REPO_URL, clone_dest)
    print(f"Repo path: {repo_path}\n")

    # Step 2: Run analyses
    timestamp = datetime.now(timezone.utc).isoformat()

    print("[1/3] Analyzing file changes...")
    file_changes = analyze_file_changes(repo_path)
    file_changes["generated_at"] = timestamp
    write_json(file_changes, "file_changes.json", output_dir)

    print("[2/3] Analyzing codebase structure...")
    structure = analyze_codebase_structure(repo_path)
    structure["generated_at"] = timestamp
    write_json(structure, "codebase_structure.json", output_dir)

    print("[3/3] Analyzing commit types...")
    commit_data = analyze_commit_types(repo_path)
    commit_data["generated_at"] = timestamp
    write_json(commit_data, "commit_types.json", output_dir)

    print("\n" + "=" * 60)
    print("Analysis complete!")
    print(f"Output directory: {output_dir}")
    print("=" * 60)


if __name__ == "__main__":
    main()
