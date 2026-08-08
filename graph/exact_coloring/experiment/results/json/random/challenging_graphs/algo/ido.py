#!/usr/bin/env python3

def ido_coloring(adj_matrix):
    """
    Colors the vertices of a graph using the Incidence Degree Ordering (IDO) algorithm.

    At each step, selects the uncolored vertex with the highest
    incidence degree (number of colored neighbors — not distinct colors,
    but the raw count of neighbors that have already been assigned a color).
    In case of a tie, the highest total degree.

    This differs from DSATUR, which uses the saturation degree (the number
    of *distinct* colors among neighbors). IDO counts *how many* neighbors
    are colored, regardless of how many distinct colors they use.

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
    # Incidence degree = number of colored neighbors (raw count, not distinct colors)
    incidence = [0] * n
    # Colors used by neighbors of each vertex (for assigning the smallest available color)
    neighbor_colors = [set() for _ in range(n)]
    neighbors = [[v for v in range(n) if adj_matrix[u][v] == 1] for u in range(n)]
    uncolored = set(range(n))

    for _ in range(n):
        # Incidence degree = number of colored neighbors (not distinct colors)
        best = max(uncolored, key=lambda v: (incidence[v], deg[v]))

        # Find the smallest color not used by neighbors
        used = neighbor_colors[best]
        c = 0
        while c in used:
            c += 1
        colors[best] = c
        uncolored.discard(best)

        # Update the incidence degree of uncolored neighbors
        for v in neighbors[best]:
            if colors[v] == -1:
                incidence[v] += 1
                neighbor_colors[v].add(c)

    nb_colors = max(colors) + 1
    return colors, nb_colors