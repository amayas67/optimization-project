#!/usr/bin/env python3
"""
compare.py — Re-runs all coloring algorithms on JSON graph instances.

For each JSON file the script:
  1. loads the adjacency matrix from `instance.adjacency_matrix`,
  2. runs every activated algorithm below,
  3. rebuilds the JSON with fresh results / ground_truth / labels,
  4. overwrites the original file,
  5. moves it into an "<n>_vertices" subfolder (n = number of vertices)
     so that full_report.py can aggregate the per-size reports.

Usage:
    python compare.py
"""

import json
import os
import shutil
import sys
import time
from datetime import datetime

# ===========================================================================
# CONFIGURATION
# ===========================================================================

# Directory containing the JSON files to process.
# Leave "" to use this script's own directory, or set an absolute/relative path,
# e.g.  JSON_DIR = "graph/exact_coloring/experiment/results/json/random/60_vertices"
JSON_DIR = ""

# Directory containing the coloring algorithms (where the algo/*.py files live).
# Leave "" for automatic detection (searches this script's directory and its
# parents for "graph/exact_coloring/algo"), or set an absolute/relative path,
# e.g.  ALGO_DIR = "graph/exact_coloring/algo"
ALGO_DIR = ""

# ===========================================================================
# Paths
# ===========================================================================
# Directory where this script lives.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Resolve the JSON directory: user value if provided, else the script's folder.
if JSON_DIR.strip():
    TARGET_DIR = JSON_DIR if os.path.isabs(JSON_DIR) else os.path.join(SCRIPT_DIR, JSON_DIR)
else:
    TARGET_DIR = SCRIPT_DIR
TARGET_DIR = os.path.abspath(TARGET_DIR)

# Resolve the algorithm directory: user value if provided, else auto-detect.
# Auto-detection searches upward from this script's directory until it finds
# "graph/exact_coloring/algo".
def _find_algo_dir():
    current = SCRIPT_DIR
    while True:
        candidate = os.path.join(current, "graph", "exact_coloring", "algo")
        if os.path.isdir(candidate):
            return candidate
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent

if ALGO_DIR.strip():
    ALGO_PATH = ALGO_DIR if os.path.isabs(ALGO_DIR) else os.path.join(SCRIPT_DIR, ALGO_DIR)
    ALGO_PATH = os.path.abspath(ALGO_PATH)
else:
    ALGO_PATH = _find_algo_dir()

if ALGO_PATH is None:
    sys.exit(f"[compare.py] Algorithm directory 'graph/exact_coloring/algo' not found "
             f"from {SCRIPT_DIR} or any parent directory — set ALGO_DIR explicitly.")
if not os.path.isdir(ALGO_PATH):
    sys.exit(f"[compare.py] Algorithm directory not found: {ALGO_PATH}")
sys.path.insert(0, ALGO_PATH)

# ===========================================================================
# Algorithm imports
# ===========================================================================
from greedy import greedy_coloring
from backtrack import backtrack_coloring
from dsatur import dsatur_coloring
from welsh_powell import welsh_powell_coloring
from smallest_degree_last import smallest_degree_last_coloring
from random_greedy import best_random_greedy_coloring
from rlf import rlf_coloring
from ido import ido_coloring
from tabu import tabucol_coloring
from sa import sa_coloring
from hea import hea_coloring

# ===========================================================================
# Algorithm registry
# ===========================================================================
# Each entry: (machine_id, display_name, callable).
# The callable receives the adjacency matrix and returns (colors, nb_colors).
#
#   ▶  To INCLUDE an algorithm : leave its line uncommented.
#   ▶  To EXCLUDE an algorithm : comment its line with "#".
#
# Parameters mirror the ones used in experiment/main.py.
ALGORITHMS = [
    ("greedy",               "Greedy",               lambda g: greedy_coloring(g)),
    ("welsh_powell",         "Welsh-Powell",         lambda g: welsh_powell_coloring(g)),
    ("dsatur",               "DSATUR",               lambda g: dsatur_coloring(g)),
    ("ido",                  "IDO",                  lambda g: ido_coloring(g)),
    ("rlf",                  "RLF",                  lambda g: rlf_coloring(g)),
    ("smallest_degree_last", "Smallest-degree-last", lambda g: smallest_degree_last_coloring(g)),
    ("random_greedy",        "Random greedy (×10)",  lambda g: best_random_greedy_coloring(g, trials=10)),
    ("sa",                   "Simulated Annealing",  lambda g: sa_coloring(g, max_iter=20000)),
    ("hea",                  "Hybrid Evolutionary",  lambda g: hea_coloring(g, pop_size=10, max_generations=50, ls_iter=1000)),
    ("tabu",                 "Tabucol",              lambda g: tabucol_coloring(g, max_iter=1000)),
    ("backtracking",         "Backtracking (exact)", lambda g: backtrack_coloring(g)),
]
NAMES = {a: n for a, n, _ in ALGORITHMS}


# ---------------------------------------------------------------------------
# Labels
# ---------------------------------------------------------------------------

def compute_labels(resultats, chi):
    """Labels for learning:
       best_algorithm = fewest colors, then lowest time;
       optimal_algorithms = all that reach chi.
    """
    best = min(resultats, key=lambda r: (r["n_colors"], r["time_ms"]))
    optimal = [r["algorithm"] for r in resultats if r["n_colors"] == chi]
    return {
        "best_algorithm": best["algorithm"],
        "best_n_colors": best["n_colors"],
        "optimal_algorithms": optimal,
        "n_optimal_algorithms": len(optimal),
    }


# ---------------------------------------------------------------------------
# Core processing
# ---------------------------------------------------------------------------

def process_json_file(path):
    """Rerun every activated algorithm on a single JSON instance file and overwrite it."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    adj = data["instance"]["adjacency_matrix"]
    n = len(adj)
    graph_type = data["instance"].get("type", "unknown")

    print(f"  • {os.path.basename(path)}  ({graph_type}, n={n})")

    results = []
    for algo_id, name, algo in ALGORITHMS:
        t0 = time.perf_counter()
        colors, nb_colors = algo(adj)
        dt = (time.perf_counter() - t0) * 1000

        results.append({
            "algorithm": algo_id,
            "n_colors": nb_colors,
            "gap_to_chi": None,          # filled after χ calculation
            "optimal": None,
            "time_ms": round(dt, 3),
            "solution": colors,
        })

    # χ = result from backtracking (exact algorithm) if present,
    # otherwise fallback to the best heuristic result.
    bt = next((r for r in results if r["algorithm"] == "backtracking"), None)
    if bt is not None:
        chi = bt["n_colors"]
        chi_source = "backtracking"
    else:
        chi = min(r["n_colors"] for r in results)
        chi_source = "best_heuristic"

    for r in results:
        r["gap_to_chi"] = r["n_colors"] - chi
        r["optimal"] = (r["n_colors"] == chi)

    labels = compute_labels(results, chi)

    # Rebuild the JSON with fresh results while preserving metadata.
    data["generated_at"] = datetime.now().isoformat()
    data["ground_truth"] = {"chi": chi, "source": chi_source}
    data["results"] = results
    data["labels"] = labels

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # Move the file into an "<n>_vertices" subfolder (n = number of vertices)
    # so that full_report.py can aggregate the per-size reports.
    subfolder = os.path.join(TARGET_DIR, f"{n}_vertices")
    os.makedirs(subfolder, exist_ok=True)
    dest_path = os.path.join(subfolder, os.path.basename(path))
    if os.path.abspath(dest_path) != os.path.abspath(path):
        shutil.move(path, dest_path)
        print(f"  → moved to {f'{n}_vertices'}/{os.path.basename(path)}")

    # Terminal summary
    print("-" * 64)
    print(f"  {'Algorithm':<25} {'Colors':>8} {'Gap':>6} {'Optimal':>8} {'ms':>11}")
    print("-" * 64)
    for r in results:
        ok = "✓" if r["optimal"] else "✗"
        print(f"  {NAMES[r['algorithm']]:<25} {r['n_colors']:>8} "
              f"{r['gap_to_chi']:>+6} {ok:>8} {r['time_ms']:>11.2f}")
    print("-" * 64)
    print(f"  χ = {chi}   ·   best: {NAMES[labels['best_algorithm']]}")
    print()


def main():
    if not os.path.isdir(TARGET_DIR):
        sys.exit(f"[compare.py] Target directory not found: {TARGET_DIR}")

    json_files = sorted(
        f for f in os.listdir(TARGET_DIR)
        if f.endswith(".json") and os.path.isfile(os.path.join(TARGET_DIR, f))
    )

    if not json_files:
        print(f"[compare.py] No JSON files found in {TARGET_DIR}")
        return

    print(f"[compare.py] Target directory: {TARGET_DIR}")
    print(f"[compare.py] Found {len(json_files)} JSON file(s)")
    print(f"[compare.py] {len(ALGORITHMS)} algorithm(s): {', '.join(a for a, _, _ in ALGORITHMS)}")
    print()

    for filename in json_files:
        process_json_file(os.path.join(TARGET_DIR, filename))

    print(f"[compare.py] Done — {len(json_files)} file(s) updated.")


if __name__ == "__main__":
    main()
