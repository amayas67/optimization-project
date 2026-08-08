#!/usr/bin/env python3
"""
Google OR-Tools CP-SAT solver for Graph Coloring.
Uses the CP-SAT (Constraint Programming) solver from OR-Tools.
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
        Number of colors used.
    """
    n = len(adj_matrix)
    if n == 0:
        return [], 0

    model = cp_model.CpModel()
    rng = cp_model.LinearExpr
    solver = cp_model.CpSolver()
    
    solver.parameters.max_time_in_seconds = time_limit
    if seed is not None:
        solver.parameters.random_seed = seed

    edges = []
    for u in range(n):
        for v in range(u + 1, n):
            if adj_matrix[u][v]:
                edges.append((u, v))

    best_k = None
    best_colors = None

    # Start with greedy upper bound
    from .common import _greedy_coloring, _matrix_to_adj_list
    adj_list = _matrix_to_adj_list(adj_matrix)
    _, greedy_k = _greedy_coloring(adj_list)
    
    for k in range(1, greedy_k + 1):
        colors = [model.NewIntVar(0, k - 1, f'c_{i}') for i in range(n)]

        for u, v in edges:
            model.Add(colors[u] != colors[v])

        solver.parameters.max_time_in_seconds = min(time_limit, time_limit / k)

        status = solver.Solve(model)

        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            solution = [solver.Value(colors[i]) for i in range(n)]
            if best_k is None or k < best_k:
                best_k = k
                best_colors = solution
                if status == cp_model.OPTIMAL:
                    break
        model = cp_model.CpModel()

    if best_colors is None:
        best_colors = [0] * n
        best_k = 1

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
        from .common import _greedy_coloring, _matrix_to_adj_list
        adj_list = _matrix_to_adj_list(adj_matrix)
        _, greedy_k = _greedy_coloring(adj_list)
        return [0] * n, greedy_k