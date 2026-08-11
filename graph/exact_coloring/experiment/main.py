#!/usr/bin/env python3
"""
main.py — Comparison of coloring algorithms on the same graph.

Generates a graph of a chosen type, applies the 13 portfolio algorithms,
displays terminal reports, then exports:
  • a "machine-ready" JSON in results/json/<type>/  (flat features,
    precomputed labels, raw matrix → ready for machine learning);

Usage:
    python main.py
"""

import json
import math
import os
import re
import shutil
import sys
import time
import random
from datetime import datetime

# ===========================================================================
# Graph generators imports
# ===========================================================================
# Each generator returns an n×n adjacency matrix (list[list[int]]),
# symmetric, with zero diagonal. 1 = edge, 0 = no edge.
# ===========================================================================

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "generation_graph"))

from generate_complet import generate_complete_adjacency_matrix
from generate_bipartite import generate_bipartite_adjacency_matrix
from generate_graph_random import generate_random_adjacency_matrix
from generate_multipartite import generate_multipartite_adjacency_matrix
from generate_tree import generate_tree_adjacency_matrix
from generate_regular import generate_regular_adjacency_matrix
from generate_cycle import generate_cycle_adjacency_matrix
from generate_wheel import generate_wheel_adjacency_matrix
from generate_grid import generate_grid_adjacency_matrix
from generate_hypercube import generate_hypercube_adjacency_matrix
from generate_mycielski import generate_mycielski_adjacency_matrix

# ===========================================================================
# Coloring algorithms imports
# ===========================================================================
# Each algorithm takes an adjacency matrix and returns:
#   colors : list[int] — color of each vertex
#   nb_colors : int    — number of colors used
# ===========================================================================

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "algo"))

from greedy import greedy_coloring
from backtrack import backtrack_coloring
from dsatur import dsatur_coloring
from welsh_powell import welsh_powell_coloring
from smallest_degree_last import smallest_degree_last_coloring
from random_greedy import random_greedy_coloring, best_random_greedy_coloring
from rlf import rlf_coloring
from ido import ido_coloring
from tabu import tabucol_coloring
from sa import sa_coloring
from hea import hea_coloring
from cpsat import cpsat_coloring
from sat import sat_coloring

# ===========================================================================
# Hard-timeout guard for exact solvers (mirrors challenging_graphs/compare.py)
# ===========================================================================
# pysat's native timer is not always reliable on UNSAT instances, and CP-SAT /
# SAT can hang on large dense graphs. We run each exact solver in a separate
# process and kill it if it exceeds main_kill, so the pipeline never blocks.
#
# Two distinct limits:
#   * time_limit : budget passed to the solver itself (per k, for solvers that
#     accept it, e.g. cpsat/sat). Soft, graceful stop.
#   * main_kill  : hard process-level kill in main.py. If exceeded, the process
#     is terminated and the result is marked TIMEOUT.
#
# IMPORTANT: backtracking is the ground-truth solver (it provides the true χ).
# It must NEVER be time-limited — a timeout would corrupt χ. If backtracking is
# still running we wait for it (no kill, no greedy fallback); only on a real
# error is the result marked TIMEOUT (n_colors = -1), never silently, and the
# run continues without any greedy substitute.

def _safe_exact_worker(q, fn, adj, tl):
    """Module-level worker so it can be pickled by multiprocessing."""
    import inspect
    try:
        kwargs = {}
        if "time_limit" in inspect.signature(fn).parameters:
            kwargs["time_limit"] = tl
        colors, nb = fn(adj, **kwargs)
        q.put(("ok", (colors, nb)))
    except Exception as exc:  # noqa: BLE001
        q.put(("error", str(exc)))


def _safe_exact(func, adj_matrix, time_limit=None, main_kill=40):
    """Run a solver with a hard process-level kill (main_kill).

    *time_limit* (seconds) is forwarded to the solver (if it accepts a
    ``time_limit`` parameter) as its per-k budget. It is ignored for solvers
    that do not accept it (e.g. backtracking).

    *main_kill* (seconds) is the hard ceiling: if the whole call exceeds it,
    main.py kills the process and marks the result as TIMEOUT.

    - backtracking: main_kill=1810 (30 min; no time_limit, never auto-limited)
    - other exact solvers (cpsat, sat): time_limit=30, main_kill=40
    """
    import multiprocessing
    from multiprocessing import Queue

    func_name = getattr(func, "__name__", "")
    hard_timeout = main_kill

    q = Queue()
    p = multiprocessing.Process(
        target=_safe_exact_worker, args=(q, func, adj_matrix, time_limit))
    p.start()

    p.join(hard_timeout)

    if p.is_alive():
        p.terminate()
        p.join(1)
        if p.is_alive():
            p.kill()
        print(f"  ⚠ {func_name} timed out (> {hard_timeout}s) — result marked as TIMEOUT")
        return [], -1

    if q.empty():
        print(f"  ⚠ {func_name} produced no result — marked as TIMEOUT")
        return [], -1

    status, payload = q.get()
    if status == "ok":
        return payload
    print(f"  ⚠ {func_name} errored ({payload}) — marked as TIMEOUT")
    return [], -1


# ===========================================================================
# Matplotlib display (removed — main.py is batch-only / minimalist)
# ===========================================================================

# Interactive graph drawing (matplotlib) removed for a minimalist, batch-only main.



# ---------------------------------------------------------------------------
# Terminal report
# ---------------------------------------------------------------------------

_PALETTE = [
    "#F5A83C", "#2FBFAE", "#EE7FA9", "#7B9CF5",
    "#A3D65C", "#F0795B", "#5AC8E8", "#C88BE0",
    "#E8C547", "#63D6B1", "#D98AD9", "#8FB8FF",
]


def _palette(nb):
    if nb <= len(_PALETTE):
        return _PALETTE[:nb]
    return _PALETTE * ((nb // len(_PALETTE)) + 1)


def _swatch(hexcolor):
    if not sys.stdout.isatty():
        return "⬤"
    r, g, b = (int(hexcolor[i:i + 2], 16) for i in (1, 3, 5))
    return f"\033[38;2;{r};{g};{b}m⬤\033[0m"


def print_report(algo, adj, colors, nb_colors, elapsed_ms=None):
    n = len(adj)
    m = sum(adj[i][j] for i in range(n) for j in range(i + 1, n))
    delta = max((sum(row) for row in adj), default=0)
    used = sorted(set(colors))
    palette = _palette(len(used))
    print(f"┌─ {algo} " + "─" * max(0, 42 - len(algo)))
    print(f"│ vertices  {n:<8} edges    {m}")
    print(f"│ colors    {nb_colors:<8} Δ        {delta}")
    if elapsed_ms is not None:
        print(f"│ time      {elapsed_ms:.2f} ms")
    print("│ palette   " + "  ".join(
        f"{_swatch(palette[k])}×{colors.count(c)}" for k, c in enumerate(used)))
    sol = str(colors)
    print(f"│ solution  {sol if len(sol) <= 46 else sol[:43] + '...'}")
    print("└" + "─" * 44)


# ---------------------------------------------------------------------------
# Graph characterization — "machine-ready" features (snake_case keys)
# ---------------------------------------------------------------------------

def _is_bipartite(adj):
    n = len(adj)
    color = [-1] * n
    for start in range(n):
        if color[start] != -1:
            continue
        color[start] = 0
        queue = [start]
        while queue:
            u = queue.pop()
            for v in range(n):
                if adj[u][v] == 1:
                    if color[v] == -1:
                        color[v] = 1 - color[u]
                        queue.append(v)
                    elif color[v] == color[u]:
                        return False
    return True


def _connected_components(adj):
    n = len(adj)
    seen = [False] * n
    nb = 0
    for start in range(n):
        if seen[start]:
            continue
        nb += 1
        stack = [start]
        seen[start] = True
        while stack:
            u = stack.pop()
            for v in range(n):
                if adj[u][v] == 1 and not seen[v]:
                    seen[v] = True
                    stack.append(v)
    return nb


def _girth(adj):
    n = len(adj)
    best = float("inf")
    for s in range(n):
        dist = [-1] * n
        parent = [-1] * n
        dist[s] = 0
        queue = [s]
        while queue:
            u = queue.pop(0)
            for v in range(n):
                if adj[u][v] != 1:
                    continue
                if dist[v] == -1:
                    dist[v] = dist[u] + 1
                    parent[v] = u
                    queue.append(v)
                elif parent[u] != v and parent[v] != u:
                    best = min(best, dist[u] + dist[v] + 1)
    return best if best != float("inf") else None


def _omega_lower_bound(adj):
    n = len(adj)
    order = sorted(range(n), key=lambda i: sum(adj[i]), reverse=True)
    clique = []
    for u in order:
        if all(adj[u][v] == 1 for v in clique):
            clique.append(u)
    return len(clique)


def graph_features(adj):
    """
    Flat structural features, ready for ML (snake_case keys,
    numeric or boolean values). `degree_sequence` is kept for
    advanced usage (excluded from the DataFrame by the loader).
    """
    n = len(adj)
    degrees = [sum(row) for row in adj]
    m = sum(degrees) // 2
    density = (2 * m / (n * (n - 1))) if n > 1 else 0.0
    avg_degree = (2 * m / n) if n else 0.0
    variance = (sum((d - avg_degree) ** 2 for d in degrees) / n) if n else 0.0
    return {
        "n": n,
        "m": m,
        "density": round(density, 6),
        "avg_degree": round(avg_degree, 4),
        "degree_std": round(math.sqrt(variance), 4),
        "delta_max": max(degrees) if degrees else 0,
        "delta_min": min(degrees) if degrees else 0,
        "bipartite": _is_bipartite(adj),
        "connected_components": _connected_components(adj),
        "girth": _girth(adj),                 # None if acyclic
        "omega_lower_bound": _omega_lower_bound(adj),
        "degree_sequence": degrees,
    }


def compute_labels(resultats, chi):
    """
    Labels for learning:
      best_algorithm = fewest colors, then lowest time;
      optimal_algorithms = all that reach χ.
    """
    computed = [r for r in resultats if r["n_colors"] >= 0]
    if computed:
        best = min(computed, key=lambda r: (r["n_colors"], r["time_ms"]))
        best_algorithm = best["algorithm"]
        best_n_colors = best["n_colors"]
    else:
        best_algorithm = ""
        best_n_colors = -1
    if chi >= 0:
        optimal = [r["algorithm"] for r in resultats
                   if r["n_colors"] >= 0 and r["n_colors"] == chi]
    else:
        optimal = []
    return {
        "best_algorithm": best_algorithm,
        "best_n_colors": best_n_colors,
        "optimal_algorithms": optimal,
        "n_optimal_algorithms": len(optimal),
    }


# ---------------------------------------------------------------------------
# Sequential file naming
# ---------------------------------------------------------------------------

def _next_sequence_index(directory, extension):
    """
    Returns the next sequential index for a file in `directory`.

    Scans existing files matching `*.{extension}` and returns the highest
    numeric prefix + 1. If the directory is empty, returns 1.
    """
    os.makedirs(directory, exist_ok=True)
    max_idx = 0
    for filename in os.listdir(directory):
        if not filename.endswith(f".{extension}"):
            continue
        stem = filename[: -len(extension) - 1]  # remove ".ext"
        if stem.isdigit():
            max_idx = max(max_idx, int(stem))
    return max_idx + 1


# ---------------------------------------------------------------------------
# JSON export — "machine-ready" format
# ---------------------------------------------------------------------------

def export_json(graph_type, params, adj, feats, resultats, chi, labels, seed, seq_index,
                chi_source="backtracking"):
    """
    Saves a self-descriptive sample in results/json/<type>/.

    Structure designed for ML:
      features      → X (flat feature vector)
      labels        → y (best_algorithm for classification)
      results       → per-algorithm details (gap, optimality, time, solution)
      instance      → reproducible raw data (matrix + seed)
    """
    folder = os.path.join(os.path.dirname(__file__), "results", "json", graph_type)
    os.makedirs(folder, exist_ok=True)
    run_id = f"{seq_index:06d}"
    path = os.path.join(folder, f"{run_id}.json")

    data = {
        "schema_version": "1.0",
        "run_id": run_id,
        "generated_at": datetime.now().isoformat(),
        "seed": seed,
        "instance": {
            "type": graph_type,
            "params": params,
            "n_vertices": feats["n"],
            "n_edges": feats["m"],
            "adjacency_matrix": adj,
        },
        "features": feats,
        "ground_truth": {"chi": chi, "source": chi_source},
        "results": resultats,
        "labels": labels,
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✓ JSON (machine): {path}")
    return path


# ---------------------------------------------------------------------------
# ML loader: results/json/** → pandas DataFrame
# ---------------------------------------------------------------------------

def load_data(root=None, format="long"):
    """
    Aggregates all JSON files from results/json/ into a pandas DataFrame.

    format="long": one row per (instance, algorithm)
                   → X = features, y = optimal / n_colors / gap_to_chi.
    format="wide": one row per instance
                   → X = features, y = labels.best_algorithm.
    """
    try:
        import pandas as pd
    except ImportError:
        print("pandas is required to load the corpus: pip install pandas")
        return None

    if root is None:
        root = os.path.join(os.path.dirname(__file__), "results", "json")

    rows = []
    for type_dir in sorted(os.listdir(root)):
        dir_path = os.path.join(root, type_dir)
        if not os.path.isdir(dir_path):
            continue
        for filename in sorted(os.listdir(dir_path)):
            if not filename.endswith(".json"):
                continue
            with open(os.path.join(dir_path, filename), encoding="utf-8") as f:
                d = json.load(f)
            base = {"run_id": d["run_id"], "type": d["instance"]["type"],
                    "chi": d["ground_truth"]["chi"]}
            base.update({k: v for k, v in d["features"].items() if k != "degree_sequence"})
            if format == "wide":
                base["best_algorithm"] = d["labels"]["best_algorithm"]
                base["best_n_colors"] = d["labels"]["best_n_colors"]
                base["n_optimal_algorithms"] = d["labels"]["n_optimal_algorithms"]
                rows.append(base)
            else:
                for r in d["results"]:
                    row = dict(base)
                    row.update({"algorithm": r["algorithm"], "n_colors": r["n_colors"],
                                "gap_to_chi": r["gap_to_chi"], "optimal": r["optimal"],
                                "time_ms": r["time_ms"]})
                    rows.append(row)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Demonstration: generation, comparison, exports
# ---------------------------------------------------------------------------

if __name__ == "__main__":

    # === Configuration =====================================================
    SEED = None          # fix an integer (e.g. 42) for a reproducible corpus
    loop_nb = 296    # number of graphs to generate and color in a row

    # -----------------------------------------------------------------------
    # Mode selector
    # -----------------------------------------------------------------------
    # operate_on_existing_json == 0 → GENERATION mode (build graphs, below).
    # operate_on_existing_json == 1 → JSON mode: instead of generating graphs,
    #   main.py reads every *.json inside JSON_DIR, runs the portfolio on each,
    #   and writes the recomputed results back (originals are preserved in a
    #   new/ subfolder). main.py is "smart": it only (re)computes the
    #   algorithms listed in ALGORITHMS and KEEPS the previous result of any
    #   algorithm you commented out below. So to skip an algorithm, simply
    #   comment its line — no separate add/del lists needed.
    operate_on_existing_json = 1
    JSON_DIR = os.path.join(os.path.dirname(__file__), "results", "json", "random","challenging_graphs")

    # Graph type to generate — choose a number:
    #   1  → random       (Erdős–Rényi G(n, p))
    #   2  → bipartite    (random bipartite graph)
    #   3  → complete     (complete graph K_n)
    #   4  → multipartite (complete k-partite graph)
    #   5  → tree         (random tree via Prüfer)
    #   6  → regular      (random d-regular graph)
    #   7  → cycle        (cycle C_n)
    #   8  → wheel        (wheel W_n)
    #   9  → grid         (2D grid rows × cols)
    #   10 → hypercube    (hypercube Q_d)
    #   11 → mycielski    (Mycielski graph M_k, triangle-free, χ = k)
    generate = 1  # you can modify this value to choose another graph

    GENERATORS = {
        1: "random", 2: "bipartite", 3: "complete", 4: "multipartite",
        5: "tree", 6: "regular", 7: "cycle", 8: "wheel",
        9: "grid", 10: "hypercube", 11: "mycielski",
    }
    GRAPH_TYPE = GENERATORS[generate]

    # Parameters for each graph type (modify as needed):
    #   random       → n: number of vertices, p: edge probability (0 ≤ p ≤ 1)
    #                  m: exact number of edges (optionnel, remplace p si fourni).
    #                  Condition : 0 ≤ m ≤ n*(n-1)/2 (max arêtes d'un graphe simple).
    #   bipartite    → u: partition U vertices, v: partition V vertices, p: U–V edge probability
    #   complete     → n: number of vertices (χ = n)
    #   multipartite → group_sizes: list of each group's size (ex: [2, 2, 2] → χ = 3)
    #   tree         → n: number of vertices (χ = 2 if n ≥ 2)
    #   regular      → n: number of vertices, d: degree of each vertex (n×d must be even)
    #   cycle        → n: number of vertices (χ = 2 if n even, 3 if n odd)
    #   wheel         → n: total number of vertices, vertex 0 = center (χ = 3 or 4)
    #   grid         → rows: number of rows, cols: number of columns (χ = 2)
    #   hypercube    → d: dimension (2^d vertices, χ = 2)
    #   mycielski    → k: index (M_k has χ = k, triangle-free; M_2 = K_2, M_3 = C_5)
    PARAMS = {
        "random":       {"n": 50, "p": 0.6},   #p means edge probability or  you can choose t il manully by replacing p with m the exact number of edges
        "bipartite":    {"u": 5, "v": 5, "p": 0.5},
        "complete":     {"n": 8},
        "multipartite": {"group_sizes": [2, 2, 2]},
        "tree":         {"n": 16},
        "regular":      {"n": 10, "d": 3},
        "cycle":        {"n": 10},
        "wheel":        {"n": 10},
        "grid":         {"rows": 3, "cols": 4},
        "hypercube":    {"d": 3},
        "mycielski":    {"k": 4},
    }

    # (machine_id, display_name, function)
    # In JSON mode, comment out an entry to DISABLE that algorithm (its
    # previous result in the JSON is then preserved instead of being recomputed).
    ALGORITHMS = [
        # ("greedy",               "Greedy",               lambda g: greedy_coloring(g)),
        # ("welsh_powell",         "Welsh-Powell",         lambda g: welsh_powell_coloring(g)),
        # ("dsatur",               "DSATUR",               lambda g: dsatur_coloring(g)),
        # ("ido",                  "IDO",                  lambda g: ido_coloring(g)),
        # ("rlf",                  "RLF",                  lambda g: rlf_coloring(g)),
        # ("smallest_degree_last", "Smallest-degree-last", lambda g: smallest_degree_last_coloring(g)),
        # ("random_greedy",        "Random greedy (×10)",  lambda g: best_random_greedy_coloring(g, trials=10)),
        # ("sa",                   "Simulated Annealing",  lambda g: sa_coloring(g, max_iter=20000)),
        # ("hea",                  "Hybrid Evolutionary",  lambda g: hea_coloring(g, pop_size=10, max_generations=50, ls_iter=1000)),
        # ("tabu",                 "Tabucol",              lambda g: tabucol_coloring(g, max_iter=20000)),
        ("cpsat",                "CP-SAT (OR-Tools)",    lambda g: _safe_exact(cpsat_coloring, g, time_limit=50, main_kill=80)),
        ("sat",                  "SAT",                  lambda g: _safe_exact(sat_coloring, g, time_limit=50, main_kill=80)),
        # ("backtracking",         "Backtracking (exact)", lambda g: _safe_exact(backtrack_coloring, g, main_kill=1810)),
    ]
    NAMES = {a: n for a, n, _ in ALGORITHMS}

    # Algorithms to REMOVE from existing JSON results in JSON mode.
    # Every entry is commented out by default (so nothing is deleted). To drop
    # an algorithm from the processed JSON files, simply uncomment its line.
    DEL_ALGORITHME = [
        # "greedy",
        # "welsh_powell",
        # "dsatur",
        # "ido",
        # "rlf",
        # "smallest_degree_last",
        # "random_greedy",
        # "sa",
        # "hea",
        # "tabu",
        # "cpsat",
        # "sat",
        # "backtracking",
    ]

    # === JSON mode =========================================================
    if operate_on_existing_json:
        json_files = [os.path.join(JSON_DIR, f)
                      for f in sorted(os.listdir(JSON_DIR)) if f.endswith(".json")]
        if not json_files:
            print(f"No JSON files found in {JSON_DIR}")
        del_ids = set(DEL_ALGORITHME)

        # Processed JSON are written into an `update/` subfolder alongside the
        # source files, so the originals are never overwritten.
        UPDATE_DIR = os.path.join(JSON_DIR, "update")
        os.makedirs(UPDATE_DIR, exist_ok=True)

        for path in json_files:
            print(f"\n{'#' * 64}")
            print(f"#  {os.path.basename(path)}")
            print(f"{'#' * 64}\n")

            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            instance = data.get("instance", data)
            adj = [list(map(int, row)) for row in
                   instance.get("adjacency_matrix",
                                instance.get("matrix", instance.get("adj", [])))]
            n = len(adj)
            feats = graph_features(adj)

            existing = data.get("results")
            existing_by_id = {r.get("algorithm"): r for r in (existing or [])}

            # Algorithms that still need to be (re)computed: enabled, not in
            # DEL_ALGORITHME, and not already present in the file's results.
            algos_to_compute = [
                (algo_id, name, algo) for algo_id, name, algo in ALGORITHMS
                if algo_id not in del_ids and algo_id not in existing_by_id
            ]

            # If every selected algorithm is already present, there is nothing to
            # recompute: copy the original file as-is into `update/`.
            if not algos_to_compute:
                out_path = os.path.join(UPDATE_DIR, os.path.basename(path))
                shutil.copy2(path, out_path)
                print(f"✓ déjà complet — copié {out_path}")
                continue

            # Recompute only the missing algorithms.
            computed = {}
            for algo_id, name, algo in algos_to_compute:
                t0 = time.perf_counter()
                colors, nb_colors = algo(adj)
                dt = (time.perf_counter() - t0) * 1000

                print_report(f"{name} (n={n})", adj, colors, nb_colors, dt)
                print()

                computed[algo_id] = {
                    "algorithm": algo_id,
                    "n_colors": nb_colors,
                    "gap_to_chi": None,          # filled after χ calculation
                    "optimal": None,
                    "time_ms": round(dt, 3),
                    "solution": colors,
                }

            # Merge: freshly computed + preserved existing results, minus any
            # algorithm listed in DEL_ALGORITHME. Algorithms already present are
            # kept untouched (never overwritten).
            results = list(computed.values())
            for algo_id, r in existing_by_id.items():
                if algo_id not in del_ids:
                    results.append(r)
            results.sort(key=lambda r: (r["n_colors"] if r["n_colors"] >= 0 else 1 << 30))

            # χ = result from backtracking (exact algorithm) if present,
            # otherwise fallback to the best heuristic result.
            bt = next((r for r in results
                       if r["algorithm"] == "backtracking" and r["n_colors"] >= 0), None)
            if bt is not None:
                chi = bt["n_colors"]
                chi_source = "backtracking"
            else:
                computed_valid = [r["n_colors"] for r in results if r["n_colors"] >= 0]
                chi = min(computed_valid) if computed_valid else -1
                chi_source = "best_heuristic" if computed_valid else "unknown"
            for r in results:
                ok = r["n_colors"] >= 0
                r["gap_to_chi"] = (r["n_colors"] - chi) if (chi >= 0 and ok) else None
                r["optimal"] = (chi >= 0 and ok and r["n_colors"] == chi)
            labels = compute_labels(results, chi)

            # Terminal summary
            print("=" * 64)
            print(f"  {'Algorithm':<25} {'Colors':>8} {'Gap':>6} {'Optimal':>8} {'ms':>11}")
            print("-" * 64)
            for r in results:
                ok = "✓" if r["optimal"] else "✗"
                gap = r["gap_to_chi"]
                gap_str = f"{gap:+d}" if gap is not None else "-"
                print(f"  {NAMES.get(r['algorithm'], r['algorithm']):<25} {r['n_colors']:>8} "
                      f"{gap_str:>6} {ok:>8} {r['time_ms']:>11.2f}")
            print("=" * 64)
            print(f"  χ = {chi}   ·   best: {NAMES.get(labels['best_algorithm'], labels['best_algorithm'])}")
            print()

            # Write the processed JSON into the `update/` subfolder, preserving
            # the original file untouched.
            out_path = os.path.join(UPDATE_DIR, os.path.basename(path))
            output = dict(data)
            output["ground_truth"] = {
                "chi": chi,
                "source": chi_source,
            }
            output["results"] = results
            output["labels"] = labels
            output["generated_at"] = datetime.now().isoformat()
            with open(out_path, "w", encoding="utf-8") as fh:
                json.dump(output, fh, ensure_ascii=False, indent=2)
            print(f"✓ wrote {out_path}")

    else:
        # === Generation ===================================================
        params = PARAMS[GRAPH_TYPE]
        generators = {
            "random":       lambda p: generate_random_adjacency_matrix(**p),
            "bipartite":    lambda p: generate_bipartite_adjacency_matrix(**p),
            "complete":     lambda p: generate_complete_adjacency_matrix(**p),
            "multipartite": lambda p: generate_multipartite_adjacency_matrix(**p),
            "tree":         lambda p: generate_tree_adjacency_matrix(**p),
            "regular":      lambda p: generate_regular_adjacency_matrix(**p),
            "cycle":        lambda p: generate_cycle_adjacency_matrix(**p),
            "wheel":        lambda p: generate_wheel_adjacency_matrix(**p),
            "grid":         lambda p: generate_grid_adjacency_matrix(**p),
            "hypercube":    lambda p: generate_hypercube_adjacency_matrix(**p),
            "mycielski":    lambda p: generate_mycielski_adjacency_matrix(**p),
        }

        for loop_idx in range(loop_nb):
            print(f"\n{'#' * 64}")
            print(f"#  Generation {loop_idx + 1} / {loop_nb}  —  {GRAPH_TYPE}")
            print(f"{'#' * 64}\n")

            # Seed: offset by loop index so each graph differs yet stays reproducible
            current_seed = SEED + loop_idx if SEED is not None else None
            if current_seed is not None:
                random.seed(current_seed)

            adj = generators[GRAPH_TYPE](params)
            n = len(adj)
            feats = graph_features(adj)

            # === Comparison loop ===================================================
            results = []
            for algo_id, name, algo in ALGORITHMS:
                t0 = time.perf_counter()
                colors, nb_colors = algo(adj)
                dt = (time.perf_counter() - t0) * 1000

                print_report(f"{name} ({GRAPH_TYPE}, n={n})", adj, colors, nb_colors, dt)
                print()

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
            if bt is not None and bt["n_colors"] >= 0:
                chi = bt["n_colors"]
                chi_source = "backtracking"
            else:
                # ignore solvers that timed out / errored (n_colors == -1)
                computed = [r["n_colors"] for r in results if r["n_colors"] >= 0]
                chi = min(computed) if computed else -1
                chi_source = "best_heuristic" if computed else "unknown"
            for r in results:
                ok = r["n_colors"] >= 0
                r["gap_to_chi"] = (r["n_colors"] - chi) if (chi >= 0 and ok) else None
                r["optimal"] = (chi >= 0 and ok and r["n_colors"] == chi)
            labels = compute_labels(results, chi)

            # === Terminal summary ==================================================
            print("=" * 64)
            print(f"  {'Algorithm':<25} {'Colors':>8} {'Gap':>6} {'Optimal':>8} {'ms':>11}")
            print("-" * 64)
            for r in results:
                ok = "✓" if r["optimal"] else "✗"
                gap = r["gap_to_chi"]
                gap_str = f"{gap:+d}" if gap is not None else "-"
                print(f"  {NAMES[r['algorithm']]:<25} {r['n_colors']:>8} "
                      f"{gap_str:>6} {ok:>8} {r['time_ms']:>11.2f}")
            print("=" * 64)
            print(f"  χ = {chi}   ·   best: {NAMES.get(labels['best_algorithm'], labels['best_algorithm'])}")
            print()

            # === Exports ===========================================================
            json_dir = os.path.join(os.path.dirname(__file__), "results", "json", GRAPH_TYPE)
            seq_index = _next_sequence_index(json_dir, "json")
            export_json(GRAPH_TYPE, params, adj, feats, results, chi, labels, current_seed, seq_index,
                        chi_source)

        # For later aggregation: df = load_data()  (format="long" or "wide")
