#!/usr/bin/env python3
"""
SAT solver for Graph Coloring via pysat.
"""

from pysat.solvers import Glucose3


def sat_coloring(adj_matrix, time_limit=60, seed=None, verbose=False):
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
    
    best_colors = greedy_colors
    best_k = greedy_k

    # Recherche descendante : on essaie de réduire k à partir de greedy_k - 1
    for k in range(greedy_k - 1, 0, -1):
        if verbose:
            print(f"  SAT: trying k={k}")
            
        clauses = []

        # Chaque sommet a au moins une couleur
        for v in range(n):
            clauses.append([v * k + c + 1 for c in range(k)])

        # Chaque sommet a au plus une couleur
        for v in range(n):
            for c1 in range(k):
                for c2 in range(c1 + 1, k):
                    clauses.append([-(v * k + c1 + 1), -(v * k + c2 + 1)])

        # Sommets adjacents de couleurs différentes
        for u, v in edges:
            for c in range(k):
                clauses.append([-(u * k + c + 1), -(v * k + c + 1)])

        # Glucose3 n'a pas de timeout natif, mais compare.py tuera le process à 70s
        with Glucose3(bootstrap_with=clauses) as solver:
            if solver.solve():
                model = solver.get_model()
                solution = [-1] * n
                for lit in model:
                    if lit > 0:
                        var_idx = (lit - 1) % k
                        v_idx = (lit - 1) // k
                        solution[v_idx] = var_idx
                
                if -1 not in solution:
                    best_k = k
                    best_colors = solution
            else:
                # UNSAT : on ne peut pas colorier avec k couleurs, on s'arrête
                break

    return best_colors, best_k