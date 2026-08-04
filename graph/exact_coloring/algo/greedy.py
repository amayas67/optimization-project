#!/usr/bin/env python3

def greedy_coloring(adj_matrix):
    """
    Colors the vertices of a graph using the greedy algorithm.

    Traverses the vertices in increasing order (0, 1, ..., n-1) and assigns
    to each vertex the smallest color (positive integer) that is not used by
    its already colored neighbors.

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
    colors = [-1] * n

    for u in range(n):
        used = set()
        for v in range(n):
            if adj_matrix[u][v] == 1 and colors[v] != -1:
                used.add(colors[v])

        c = 0
        while c in used:
            c += 1
        colors[u] = c

    nb_colors = max(colors) + 1 if colors else 0

    return colors, nb_colors