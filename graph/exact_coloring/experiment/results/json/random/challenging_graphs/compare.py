#!/usr/bin/env python3
r"""
compare.py — Run and compare all graph-coloring algorithms from the ``algo/`` package.

Each algorithm takes an adjacency matrix (``list[list[int]]``) and returns a
``(colors, n_colors)`` tuple, exactly like the ``results`` entries stored in the
JSON instances.

Usage
-----
    # Compare all algorithms on a single graph (loads a JSON instance file)
    python compare.py "000024 (1).json"

    # Compare a few selected algorithms
    python compare.py "000024 (1).json" --algos greedy,dsatur,tabu

    # Batch-compare over every JSON file in the directory
    python compare.py --all

By default, results are written to a ``new/`` directory (created if missing)
so the original JSON files are never overwritten. Each output file keeps the
same schema as the input JSON files (``instance``, ``ground_truth``,
``results``, ``labels``), with freshly computed results replacing the old ones.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional, Tuple

# Make sure the project root (parent of algo/) is importable so that
# ``import algo`` works no matter the current working directory.
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

# Working directory (where the user runs the script from) - output goes here
_CWD = os.getcwd()

# --------------------------------------------------------------------------- #
# Correct imports of the algorithms in algo/                                #
# --------------------------------------------------------------------------- #
# Core algorithms (always available)
from algo.dsatur import dsatur_coloring                # dsatur
from algo.greedy import greedy_coloring                # greedy
from algo.ido import ido_coloring                      # ido
from algo.random_greedy import best_random_greedy_coloring  # random_greedy
from algo.rlf import rlf_coloring                      # rlf
from algo.sa import sa_coloring                        # sa
from algo.smallest_degree_last import smallest_degree_last_coloring  # smallest_degree_last
from algo.tabu import tabucol_coloring                 # tabu
from algo.welsh_powell import welsh_powell_coloring    # welsh_powell

# Optional algorithms (may require extra dependencies)
try:
    from algo.backtrack import backtrack_coloring      # backtracking
except ImportError:
    backtrack_coloring = None

try:
    from algo.cpsat import cpsat_coloring              # cp-sat
except ImportError:
    cpsat_coloring = None

try:
    from algo.hea import hea_coloring                  # hea
except ImportError:
    hea_coloring = None

try:
    from algo.sat import sat_coloring                  # sat
except ImportError:
    sat_coloring = None


# --------------------------------------------------------------------------- #
# Registry: maps the JSON "algorithm" name to the callable.                  #
# This mirrors the names used in the ``results`` array of every JSON file     #
# and in html_stats.py (ALGORITHMS / FIRST_TEN_ALGOS).                       #
# --------------------------------------------------------------------------- #
ALGORITHM_REGISTRY: Dict[str, Callable] = {
    "greedy":              greedy_coloring,
    "welsh_powell":        welsh_powell_coloring,
    "dsatur":              dsatur_coloring,
    "ido":                 ido_coloring,
    "rlf":                 rlf_coloring,
    "smallest_degree_last": smallest_degree_last_coloring,
    "random_greedy":       best_random_greedy_coloring,
    "sa":                  sa_coloring,
    "tabu":                tabucol_coloring,
}

# Add optional algorithms if available
if backtrack_coloring is not None:
    ALGORITHM_REGISTRY["backtracking"] = backtrack_coloring

if cpsat_coloring is not None:
    ALGORITHM_REGISTRY["cpsat"] = cpsat_coloring

if hea_coloring is not None:
    ALGORITHM_REGISTRY["hea"] = hea_coloring

if sat_coloring is not None:
    ALGORITHM_REGISTRY["sat"] = sat_coloring


def _call_algorithm(func: Callable, adj_matrix, seed: Optional[int]) -> Tuple[List[int], int]:
    """Call *func* with sensible kwargs, swallowing signature mismatches."""
    import inspect

    sig = inspect.signature(func)
    kwargs = {}
    for name in ("seed", "max_iter", "pop_size", "trials", "ls_iter", "max_generations", "k", "time_limit"):
        if name in sig.parameters:
            if name == "seed":
                kwargs["seed"] = seed
            elif name == "max_iter":
                kwargs["max_iter"] = 5000
            elif name == "pop_size":
                kwargs["pop_size"] = 5
            elif name == "trials":
                kwargs["trials"] = 5
            elif name == "ls_iter":
                kwargs["ls_iter"] = 100
            elif name == "max_generations":
                kwargs["max_generations"] = 10
            elif name == "k":
                kwargs["k"] = None
            elif name == "time_limit":
                # Give more time to exact solvers
                hard_algos = {"cpsat", "sat", "backtracking"}
                func_name = getattr(func, "__name__", "").lower()
                if any(a in func_name for a in hard_algos):
                    kwargs["time_limit"] = 60
                else:
                    kwargs["time_limit"] = 30
    
    # Algorithms that need hard process-level timeout (C extensions)
    hard_timeout_algos = {"sat", "cpsat"}
    func_name = getattr(func, "__name__", "").lower()
    needs_hard_timeout = any(algo in func_name for algo in hard_timeout_algos)
    
    if needs_hard_timeout:
        return _run_with_hard_timeout(func, adj_matrix, kwargs, kwargs.get("time_limit", 30) + 10)
    
    try:
        return func(adj_matrix, **kwargs)
    except TypeError:
        # Fallback: call with only the adj_matrix (deterministic algorithms).
        return func(adj_matrix)


def _worker_wrapper(q, func_name, adj_matrix, kwargs):
    """Worker function for multiprocessing - must be at module level for pickling."""
    import sys
    # Re-import the module to get the function
    import algo
    func = getattr(algo, func_name, None)
    if func is None:
        q.put(("error", f"Function {func_name} not found"))
        return
    try:
        result = func(adj_matrix, **kwargs)
        q.put(("ok", result))
    except Exception as e:
        q.put(("error", str(e)))


def _run_with_hard_timeout(func: Callable, adj_matrix, kwargs: dict, timeout: int) -> Tuple[List[int], int]:
    """Run function in separate process with hard timeout."""
    import multiprocessing
    from multiprocessing import Queue
    
    func_name = getattr(func, "__name__", "")
    
    q = Queue()
    p = multiprocessing.Process(target=_worker_wrapper, args=(q, func_name, adj_matrix, kwargs))
    p.start()
    p.join(timeout)
    
    if p.is_alive():
        p.terminate()
        p.join(1)
        if p.is_alive():
            p.kill()
        # Return greedy fallback
        from algo.greedy import greedy_coloring
        return greedy_coloring(adj_matrix)
    
    if q.empty():
        return [-1] * len(adj_matrix), len(adj_matrix)
    
    status, result = q.get()
    if status == "ok":
        return result
    else:
        # Error - fallback to greedy
        from algo.greedy import greedy_coloring
        return greedy_coloring(adj_matrix)


def run_algorithm(name: str, adj_matrix, seed: Optional[int] = 42) -> Tuple[List[int], int, float]:
    """
    Run a single registered algorithm on *adj_matrix*.

    Returns ``(colors, n_colors, elapsed_ms)``.
    """
    func = ALGORITHM_REGISTRY[name]
    t0 = time.perf_counter()
    colors, n_colors = _call_algorithm(func, adj_matrix, seed)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    return colors, n_colors, elapsed_ms


def run_all(adj_matrix, seed: Optional[int] = 42,
            algo_names: Optional[List[str]] = None) -> List[dict]:
    """
    Run every (or a subset of) registered algorithm on *adj_matrix*.

    Parameters
    ----------
    adj_matrix: list[list[int]]
        Symmetric n×n adjacency matrix.
    seed: int or None
        RNG seed forwarded to stochastic algorithms.
    algo_names: list[str] or None
        Subset of algorithm names (JSON keys) to run. ``None`` ⇒ all.

    Returns
    -------
    list[dict]
        One entry per algorithm, each with keys: ``algorithm``, ``n_colors``,
        ``gap_to_chi`` (0 for now, recomputed later), ``optimal``, ``time_ms``,
        ``solution``.
    """
    if algo_names is None:
        algo_names = list(ALGORITHM_REGISTRY.keys())

    print(f"  Running {len(algo_names)} algorithms: {', '.join(algo_names)}")
    
    results: List[dict] = []
    for i, name in enumerate(algo_names, 1):
        if name not in ALGORITHM_REGISTRY:
            raise KeyError(f"Unknown algorithm '{name}'. Available: {list(ALGORITHM_REGISTRY)}")
        print(f"  [{i}/{len(algo_names)}] Running {name}...", end=" ", flush=True)
        try:
            colors, n_colors, elapsed_ms = run_algorithm(name, adj_matrix, seed)
        except Exception as exc:  # noqa: BLE001
            results.append({
                "algorithm": name,
                "n_colors": -1,
                "gap_to_chi": 0,
                "optimal": False,
                "time_ms": 0.0,
                "solution": [],
                "error": str(exc),
            })
            print(f"✗ error: {exc}")
            continue
        print(f"✓ done ({n_colors} colors, {elapsed_ms:.1f}ms)")
        results.append({
            "algorithm": name,
            "n_colors": n_colors,
            "gap_to_chi": 0,      # recomputed after we know chi
            "optimal": False,     # recomputed after we know chi
            "time_ms": round(elapsed_ms, 3),
            "solution": colors,
        })

    # Sort: best (fewest colors) first.
    results.sort(key=lambda r: (r["n_colors"] if r["n_colors"] >= 0 else 1 << 30))
    return results


def load_instance(path: str) -> Tuple[dict, List[List[int]], Optional[int]]:
    """Load ``(original_data, adjacency_matrix, chi)`` from a JSON instance file.

    ``original_data`` is the full JSON object so we can preserve ``instance``,
    ``features``, ``schema_version``, ``seed``, etc.
    """
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)

    instance = data.get("instance", data)
    matrix = instance.get("adjacency_matrix", instance.get("matrix", instance.get("adj", [])))
    adj_matrix = [list(map(int, row)) for row in matrix]

    ground_truth = data.get("ground_truth", {}) or {}
    chi_raw = ground_truth.get("chi")
    chi: Optional[int] = None
    if chi_raw is not None:
        try:
            chi = int(chi_raw)
        except (TypeError, ValueError):
            chi = None
    return data, adj_matrix, chi


def build_output_json(original_data: dict, new_results: List[dict], chi: Optional[int]) -> dict:
    """
    Build a JSON object with the same schema as the input files.

    Keeps ``instance``, ``features``, ``schema_version``, ``seed``, etc.
    from the original, but replaces ``ground_truth``, ``results`` and ``labels``
    with freshly computed values.
    """
    output = dict(original_data)

    # Update ground_truth: keep chi, update source.
    ground_truth = {
        "chi": chi if chi is not None else 0,
        "source": "compare.py (fresh run)",
    }
    output["ground_truth"] = ground_truth

    # Recompute gap_to_chi and optimal flags.
    best_n = min((r["n_colors"] for r in new_results if r["n_colors"] >= 0), default=-1)
    updated_results = []
    for r in new_results:
        n = r["n_colors"]
        if n < 0:
            updated_results.append(r)
            continue
        gap = max(0, n - chi) if chi is not None else 0
        optimal = (chi is not None and n == chi)
        updated_results.append({
            "algorithm": r["algorithm"],
            "n_colors": n,
            "gap_to_chi": gap,
            "optimal": optimal,
            "time_ms": r["time_ms"],
            "solution": r["solution"],
        })

    output["results"] = updated_results

    optimal_algos = sorted([r["algorithm"] for r in updated_results if r.get("optimal")])
    output["labels"] = {
        "best_algorithm": updated_results[0]["algorithm"] if updated_results else "",
        "best_n_colors": best_n if best_n >= 0 else 0,
        "optimal_algorithms": optimal_algos,
        "n_optimal_algorithms": len(optimal_algos),
    }

    output.setdefault("generated_at", datetime.now(timezone.utc).isoformat())
    return output


def format_status(r: dict, chi: Optional[int], best_n: int) -> str:
    """Decide the displayed status of a result."""
    if r.get("error"):
        return f"✗ error ({r['error']})"
    n = r["n_colors"]
    if chi is not None and n == chi:
        return f"✓ optimal (χ={chi})"
    if n == best_n:
        return f"✓ best ({n})"
    return f"({n})"


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Compare graph-coloring algorithms from algo/.")
    parser.add_argument("file", nargs="?", help="Path to a JSON instance file.")
    parser.add_argument("--all", action="store_true",
                        help="Run on every JSON file in the current directory.")
    parser.add_argument("--algos", default=None,
                        help="Comma-separated subset of algorithm names (JSON keys).")
    parser.add_argument("--seed", type=int, default=42, help="RNG seed (default: 42).")
    parser.add_argument("--out-dir", default="new",
                        help="Directory where new JSON files are written (default: new/).")
    args = parser.parse_args(argv)

    # Use current working directory for input/output
    work_dir = _CWD

    if args.all:
        files = sorted(f for f in os.listdir(work_dir) if f.endswith(".json"))
    elif args.file:
        files = [args.file]
    else:
        parser.error("Provide a JSON file or use --all.")

    algo_names = args.algos.split(",") if args.algos else None

    out_dir = os.path.join(work_dir, args.out_dir)
    os.makedirs(out_dir, exist_ok=True)

    print(f"Processing {len(files)} file(s)...")
    
    for fname in files:
        print(f"\n{'='*60}")
        print(f"Processing file: {fname}")
        print(f"{'='*60}")
        
        path = os.path.join(work_dir, fname)
        try:
            original_data, adj_matrix, chi = load_instance(path)
        except Exception as exc:  # noqa: BLE001
            print(f"  ✗ ERROR loading — {exc}")
            continue

        run_id = os.path.splitext(fname)[0]
        new_results = run_all(adj_matrix, seed=args.seed, algo_names=algo_names)

        # Best n_colors among non-error results for this run.
        valid = [r["n_colors"] for r in new_results if r["n_colors"] >= 0]
        best_n = min(valid) if valid else -1

        output_data = build_output_json(original_data, new_results, chi)
        out_path = os.path.join(out_dir, fname)
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(output_data, fh, indent=2)
            fh.write("\n")

        chi_str = str(chi) if chi is not None else "unknown"
        print(f"\n## {run_id}   (χ = {chi_str})")
        print(f"| algorithm | n_colors | time_ms | status |")
        print(f"|---|---|---|---|")
        for r in new_results:
            print(f"| {r['algorithm']} | {r['n_colors']} | {r['time_ms']} | "
                  f"{format_status(r, chi, best_n)} |")
        print(f"\n-> {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())