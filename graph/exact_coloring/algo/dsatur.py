#!/usr/bin/env python3

def dsatur_coloring(adj_matrix):
    """
    Colors the vertices of a graph using the DSATUR algorithm.

    DSATUR (Degree of Saturation) is a greedy coloring algorithm
    that at each step selects the uncolored vertex with the highest
    saturation degree (number of different colors already used
    among its neighbors). In case of ties, the vertex with the
    highest total degree is chosen.

    Parameters
    ----------
    adj_matrix : list[list[int]]
        Symmetric n x n adjacency matrix, zero diagonal.

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

    colors = [-1] * n
    deg = [sum(row) for row in adj_matrix]
    satur = [0] * n
    # Colors used by neighbors of each vertex (as sets)
    neighbor_colors = [set() for _ in range(n)]

    # Precompute neighbors
    neighbors = [[v for v in range(n) if adj_matrix[u][v] == 1] for u in range(n)]

    # Set of uncolored vertices (sorted by (saturation, degree) at each iteration)
    uncolored = set(range(n))

    for _ in range(n):
        # Choose the vertex with the highest saturation, and in case of tie the highest degree
        u = max(uncolored, key=lambda v: (satur[v], deg[v]))

        # Find the smallest color not used by neighbors
        used = neighbor_colors[u]
        c = 0
        while c in used:
            c += 1
        colors[u] = c
        uncolored.remove(u)

        # Update the saturation of uncolored neighbors
        for v in neighbors[u]:
            if colors[v] == -1:
                neighbor_colors[v].add(c)
                satur[v] = len(neighbor_colors[v])

    nb_colors = max(colors) + 1

    return colors, nb_colors