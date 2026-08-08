#!/usr/bin/env python3
"""
no_redondance.py — Remove redundant JSON files based on the adjacency matrix.

Scans .json files in the given directory (or current directory by default).
For each file, it extracts the adjacency matrix. If the matrix has never been
seen before, the file is kept and copied into a "unique/" subfolder inside the
scanned directory. Redundant files are ignored.

Usage:
    python no_redondance.py [directory]
    directory    (optional) Directory to scan, defaults to current directory
"""

import os
import sys
import json
import shutil
import argparse

def get_adjacency_matrix(data):
    """Extract the adjacency matrix from the JSON data."""
    instance = data.get("instance")
    if instance and "adjacency_matrix" in instance:
        return instance["adjacency_matrix"]
    if "adjacency_matrix" in data:
        return data["adjacency_matrix"]
    if "matrix" in data:
        return data["matrix"]
    if "adj" in data:
        return data["adj"]
    return None

def matrix_key(matrix):
    """Convert a matrix into a hashable key (tuple of tuples)."""
    if not matrix:
        return None
    try:
        return tuple(tuple(int(x) for x in row) for row in matrix)
    except (ValueError, TypeError):
        return str(matrix)

def main():
    parser = argparse.ArgumentParser(
        description="Remove redundant JSON files based on the adjacency matrix."
    )
    parser.add_argument(
        "directory", nargs="?", default=".",
        help="Directory to scan (default: current directory)"
    )
    args = parser.parse_args()

    directory = os.path.abspath(args.directory)
    if not os.path.isdir(directory):
        print(f"Error: {directory} is not a valid directory.")
        sys.exit(1)

    json_files = [f for f in os.listdir(directory) if f.endswith(".json")]
    if not json_files:
        print(f"No JSON files found in {directory}.")
        sys.exit(0)

    seen = set()
    unique_files = []
    duplicates = []

    for filename in sorted(json_files):
        filepath = os.path.join(directory, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"Error reading {filename}: {e}")
            continue

        matrix = get_adjacency_matrix(data)
        if matrix is None:
            print(f"No adjacency matrix found in {filename}, skipping.")
            continue

        key = matrix_key(matrix)
        if key is None:
            print(f"Could not convert matrix from {filename}, skipping.")
            continue

        if key in seen:
            duplicates.append(filename)
        else:
            seen.add(key)
            unique_files.append(filename)

    total = len(json_files)
    print(f"Total JSON files: {total}")
    print(f"Unique files (distinct matrices): {len(unique_files)}")
    print(f"Redundant files: {len(duplicates)}")
    if duplicates:
        print("Redundant files:")
        for f in duplicates:
            print(f"  {f}")
    print("\nUnique files kept:")
    for f in unique_files:
        print(f"  {f}")

    # Automatically copy unique files into a "unique" subfolder
    if unique_files:
        dest_dir = os.path.join(directory, "unique")
        os.makedirs(dest_dir, exist_ok=True)
        for f in unique_files:
            src = os.path.join(directory, f)
            dst = os.path.join(dest_dir, f)
            shutil.copy2(src, dst)
        print(f"\n✅ Unique files copied to {dest_dir}")

if __name__ == "__main__":
    main()
