#!/usr/bin/env python3

def welsh_powell_coloring(adj_matrix):
    """
    Colors the vertices of a graph using the Welsh-Powell algorithm.

    Sorts vertices by decreasing degree, then applies greedy coloring
    in that order. At each step, the vertex receives the smallest color
    not used by its already colored neighbors.

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

    # Degrees of each vertex
    degrees = [sum(row) for row in adj_matrix]

    # Sort vertices by decreasing degree
    order = sorted(range(n), key=lambda i: degrees[i], reverse=True)

    colors = [-1] * n

    for u in order:
        used = set()
        for v in range(n):
            if adj_matrix[u][v] == 1 and colors[v] != -1:
                used.add(colors[v])

        c = 0
        while c in used:
            c += 1
        colors[u] = c

    nb_colors = max(colors) + 1

    return colors, nb_colors