#!/usr/bin/env python3
"""
SAT solver for Graph Coloring via pysat (Glucose3).
With internal timeout per k; on timeout/error returns best proven so far.
If nothing is ever proven, returns ([], -1) (NO greedy fallback).
"""

import threading
try:
    import multiprocessing
    from multiprocessing import Queue
    HAS_MULTIPROCESSING = True
except ImportError:
    HAS_MULTIPROCESSING = False


def _sat_solve_worker(q, clauses, n, k, time_limit):
    """Worker process: runs Glucose3 with a hard timeout."""
    try:
        from pysat.solvers import Glucose3
        with Glucose3(bootstrap_with=clauses) as solver:
            result = {"status": None, "model": None, "error": None}
            
            def solve_worker():
                try:
                    result["status"] = solver.solve()
                    if result["status"]:
                        result["model"] = solver.get_model()
                except Exception as e:
                    result["error"] = str(e)
            
            thread = threading.Thread(target=solve_worker)
            thread.daemon = True
            thread.start()
            thread.join(timeout=time_limit)
            
            if thread.is_alive():
                q.put(("timeout", None))
            elif result["error"]:
                q.put(("error", result["error"]))
            else:
                q.put((result["status"], result.get("model")))

    except Exception as e:
        q.put(("error", str(e)))


def _sat_solve_with_timeout(clauses, n, k, time_limit):
    """Run Glucose3 with hard timeout, return (status, model) or (None, None) on timeout/error."""
    if not HAS_MULTIPROCESSING:
        # Fallback: no multiprocessing, run directly (no timeout)
        from pysat.solvers import Glucose3
        with Glucose3(bootstrap_with=clauses) as solver:
            status = solver.solve()
            if status:
                model = solver.get_model()
                return True, model
            return False, None

    q = Queue()
    p = multiprocessing.Process(target=_sat_solve_worker, args=(q, clauses, n, k, time_limit))
    p.start()
    p.join(time_limit + 5)  # extra margin for process cleanup

    if p.is_alive():
        p.terminate()
        p.join(1)
        if p.is_alive():
            p.kill()
        return "timeout", None

    if q.empty():
        return None, None

    status, payload = q.get()
    if status == "timeout":
        return "timeout", None
    elif status == "error":
        return "error", None
    elif status is True:
        return True, payload
    else:  # False (UNSAT)
        return False, None


def sat_coloring(adj_matrix, time_limit=60, seed=None, verbose=False):
    """
    Colors the vertices of a graph using Glucose3 SAT solver.
    
    Strategy (mirroring CP-SAT for correctness):
    - Descend from greedy_k - 1 down to 1.
    - Full time_limit per k (no budget splitting).
    - Only accept SAT as proven; UNSAT stops (monotonicity).
    - Timeout/error per k stops search; if nothing proven, returns ([], -1).
    """
    n = len(adj_matrix)
    if n == 0:
        return [], 0

    edges = []
    for u in range(n):
        for v in range(u + 1, n):
            if adj_matrix[u][v]:
                edges.append((u, v))

    from common import _greedy_coloring, _matrix_to_adj_list
    adj_list = _matrix_to_adj_list(adj_matrix)
    greedy_colors, greedy_k = _greedy_coloring(adj_list)
    
    if greedy_k <= 1:
        return greedy_colors, greedy_k

    best_colors = None
    best_k = None

    # Descend from greedy_k - 1 down to 1
    # Full time_limit per k (no budget splitting)
    # Only accept SAT as proven; UNSAT stops (monotonicity)
    # Timeout/error per k stops search; if nothing proven, returns ([], -1).
    for k in range(greedy_k - 1, 0, -1):
        if verbose:
            print(f"  SAT: trying k={k}")

        clauses = []

        # Each vertex has at least one color
        for v in range(n):
            clauses.append([v * k + c + 1 for c in range(k)])

        # Each vertex has at most one color
        for v in range(n):
            for c1 in range(k):
                for c2 in range(c1 + 1, k):
                    clauses.append([-(v * k + c1 + 1), -(v * k + c2 + 1)])

        # Adjacent vertices different colors
        for u, v in edges:
            for c in range(k):
                clauses.append([-(u * k + c + 1), -(v * k + c + 1)])

        # Solve with per-k timeout
        status, model = _sat_solve_with_timeout(clauses, n, k, time_limit)
        
        if status is True:
            # SAT: found a valid coloring
            solution = [-1] * n
            for lit in model:
                if lit > 0:
                    var_idx = (lit - 1) % k
                    v_idx = (lit - 1) // k
                    solution[v_idx] = var_idx
            
            if -1 not in solution:
                best_k = k
                best_colors = solution
                # Proven for this k: continue to try k-1
                continue

        elif status is False:
            # UNSAT: proven impossible, by monotonicity all smaller k are also infeasible
            break

        else:  # timeout or error
            # Timeout or error: stop search, keep best proven so far
            break

    # If nothing was ever proven (timeout/error/UNSAT before any SAT),
    # return empty with -1 (NO greedy fallback, per project rule).
    if best_colors is None:
        return [], -1

    return best_colors, best_k