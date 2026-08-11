#!/usr/bin/env python3
"""
Google OR-Tools CP-SAT solver for Graph Coloring.
Uses the CP-SAT (Constraint Programming) solver from OR-Tools.

Strategy (mirroring sat.py for correctness):
- Descend from greedy_k - 1 down to 1.
- Full time_limit per k (no budget splitting).
- Only accept OPTIMAL as proven; UNKNOWN/FEASIBLE stops the loop.
- INFEASIBLE stops (monotonicity: smaller k also infeasible).
- Fallback: ([], -1) if nothing proven (no greedy fallback, per project rule).
"""

from ortools.sat.python import cp_model


def cpsat_coloring(adj_matrix, time_limit=60, seed=None, verbose=False):
    """
    Colors the vertices of a graph using OR-Tools CP-SAT solver.

    Parameters
    ----------
    adj_matrix : list[list[int]]
        Symmetric n x n adjacency matrix, zero diagonal.
    time_limit : float, optional
        Time limit in seconds (default: 60).
    seed : int, optional
        Random seed for reproducibility.
    verbose : bool, optional
        Print progress information.

    Returns
    -------
    colors : list[int]
        List of size n, color assigned to each vertex.
    nb_colors : int
        Number of colors used (proven optimal, or greedy upper bound).
    """
    n = len(adj_matrix)
    if n == 0:
        return [], 0

    edges = []
    for u in range(n):
        for v in range(u + 1, n):
            if adj_matrix[u][v]:
                edges.append((u, v))

    # Greedy upper bound (mirrors sat.py): we descend from greedy_k - 1, so we
    # only ever (try to) prove a coloring strictly better than greedy.
    from common import _greedy_coloring, _matrix_to_adj_list
    adj_list = _matrix_to_adj_list(adj_matrix)
    greedy_colors, greedy_k = _greedy_coloring(adj_list)

    if greedy_k <= 1:
        return greedy_colors, greedy_k

    best_k = None
    best_colors = None

    # Descend from greedy_k - 1 down to 1.
    # Give FULL time_limit to each k (no budget splitting).
    # Monotonicity: if k is infeasible, all smaller k are also infeasible.
    for k in range(greedy_k - 1, 0, -1):
        model = cp_model.CpModel()
        colors = [model.NewIntVar(0, k - 1, f'c_{i}') for i in range(n)]

        for u, v in edges:
            model.Add(colors[u] != colors[v])

        solver = cp_model.CpSolver()
        if seed is not None:
            solver.parameters.random_seed = seed
        # Full time_limit per k (no budget splitting).
        solver.parameters.max_time_in_seconds = time_limit

        status = solver.Solve(model)

        if status == cp_model.OPTIMAL:
            solution = [solver.Value(colors[i]) for i in range(n)]
            best_k = k
            best_colors = solution
            # Proven optimal for this k: continue to try k-1.
            continue

        if status == cp_model.INFEASIBLE:
            # Proven impossible: by monotonicity, all smaller k are also infeasible.
            break

        # UNKNOWN (or FEASIBLE): inconclusive. Stop the search.
        # Keep the best *proven* k found so far (if any).
        break

    # If nothing was ever proven optimal, return empty with -1 (NO greedy
    # fallback, per project rule — greedy is a separate algorithm).
    if best_colors is None:
        return [], -1

    return best_colors, best_k


def cpsat_coloring_fixed_k(adj_matrix, k, time_limit=60, seed=None, verbose=False):
    """
    CP-SAT variant that tries to find a valid coloring with a fixed number of colors k.
    """
    n = len(adj_matrix)
    if n == 0:
        return [], 0

    model = cp_model.CpModel()
    solver = cp_model.CpSolver()

    if seed is not None:
        solver.parameters.random_seed = seed
    solver.parameters.max_time_in_seconds = time_limit

    colors = [model.NewIntVar(0, k - 1, f'c_{i}') for i in range(n)]

    for u in range(n):
        for v in range(u + 1, n):
            if adj_matrix[u][v]:
                model.Add(colors[u] != colors[v])

    status = solver.Solve(model)

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        solution = [solver.Value(colors[i]) for i in range(n)]
        return solution, k
    else:
        # No greedy fallback: return empty with -1 (per project rule).
        return [], -1