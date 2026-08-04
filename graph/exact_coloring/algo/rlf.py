#!/usr/bin/env python3

def rlf_coloring(adj_matrix):
    """
    Colors the vertices of a graph using the Recursive Largest First (RLF) algorithm.

    Builds the color classes one by one. For each color, iteratively selects
    the uncolored vertex with the most uncolored neighbors in the current class,
    until no more vertices can be added.

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
    neighbors = [set(v for v in range(n) if adj_matrix[u][v] == 1) for u in range(n)]
    uncolored = set(range(n))
    current_color = 0

    while uncolored:
        # Current color class
        color_class = []

        # Candidates = uncolored vertices without neighbors in the current class
        candidates = set(uncolored)

        while candidates:
            # Choose the vertex with the most uncolored neighbors (outside class)
            best = max(candidates, key=lambda v: len(neighbors[v] & uncolored))
            color_class.append(best)
            candidates.discard(best)

            # Remove neighbors of the chosen vertex from candidates
            for w in neighbors[best]:
                candidates.discard(w)

        # Assign the current color
        for v in color_class:
            colors[v] = current_color
            uncolored.discard(v)

        current_color += 1

    nb_colors = current_color
    return colors, nb_colors