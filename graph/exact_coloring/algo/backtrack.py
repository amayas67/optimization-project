#!/usr/bin/env python3

def backtrack_coloring(adj_matrix):
    """
    Colors the vertices of a graph using the backtracking algorithm (exact).

    Explores all possible color assignments via backtracking
    to find the optimal chromatic number (minimum number of colors).

    Parameters
    ----------
    adj_matrix : list[list[int]]
        Symmetric n x n adjacency matrix, zero diagonal.

    Returns
    -------
    colors : list[int]
        List of size n, color assigned to each vertex (optimal coloring).
    nb_colors : int
        Chromatic number (minimum number of colors used).
    """
    n = len(adj_matrix)
    best_colors = None
    best_nb = n + 1

    # Welsh-Powell order: sort vertices by decreasing degree
    # vertices with highest degree are processed first to increase chances of finding the optimal solution quickly
    degrees = [sum(row) for row in adj_matrix]
    order = sorted(range(n), key=lambda i: degrees[i], reverse=True)

    # Precompute neighbors for each vertex
    neighbors = [[v for v in range(n) if adj_matrix[u][v] == 1] for u in range(n)]

    def is_safe(u, c, current_colors):
        # for each neighbor v of u, if v has color c, then u cannot have color c
        for v in neighbors[u]:
            if current_colors[v] == c:
                return False
        return True

    def backtrack(idx, current_colors, max_color):
        nonlocal best_colors, best_nb

        # Current number of colors = max_color + 1
        if max_color + 1 >= best_nb:
            return

        if idx == n:
            best_colors = current_colors[:]
            best_nb = max_color + 1
            return

        u = order[idx]

        for c in range(max_color + 1):
            if is_safe(u, c, current_colors):
                current_colors[u] = c
                backtrack(idx + 1, current_colors, max_color)
                current_colors[u] = -1

        # Try a new color
        if max_color + 1 < best_nb:
            current_colors[u] = max_color + 1
            backtrack(idx + 1, current_colors, max_color + 1)
            current_colors[u] = -1

    current_colors = [-1] * n
    backtrack(0, current_colors, -1)

    return best_colors, best_nb