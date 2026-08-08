#!/usr/bin/env python3

def smallest_degree_last_coloring(adj_matrix):
    """
    Colors the vertices of a graph using the Smallest Degree Last (SDL) algorithm.

    Iteratively removes the vertex with the smallest degree in the current
    graph, stacks the vertices as it goes, then colors them in the reverse
    order of their removal (last removed = first colored) with standard greedy
    coloring.

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

    # Copy the matrix to modify it
    mat = [row[:] for row in adj_matrix]
    # Current degrees
    deg = [sum(row) for row in mat]
    # Marked as removed
    removed = [False] * n
    # Removal order (stack)
    stack = []

    for _ in range(n):
        # Find the non-removed vertex with the smallest degree
        u = min((i for i in range(n) if not removed[i]), key=lambda i: deg[i])
        stack.append(u)
        removed[u] = True

        # Decrement the degrees of neighbors still present
        for v in range(n):
            if mat[u][v] == 1 and not removed[v]:
                deg[v] -= 1

    # Color in reverse order of the stack
    colors = [-1] * n

    while stack:
        u = stack.pop()
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