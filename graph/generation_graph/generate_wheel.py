#!/usr/bin/env python3

def generate_wheel_adjacency_matrix(n):
    """
    Generates an adjacency matrix for a wheel W_n.

    A wheel W_n is a cycle C_{n-1} with an additional central vertex
    connected to all others. Vertex 0 is the center, vertices 1 to n-1
    form the cycle.
    χ = 3 if n-1 is even, 4 if n-1 is odd (n ≥ 4).

    Parameters
    ----------
    n : int
        Total number of vertices (n ≥ 4, vertex 0 = center).

    Returns
    -------
    list[list[int]]
        Symmetric n x n adjacency matrix, zero diagonal.
    """
    if n < 0:
        return []
    if n <= 1:
        return [[0] * n for _ in range(n)]

    mat = [[0] * n for _ in range(n)]

    # Vertex 0 = center, connected to all others
    for i in range(1, n):
        mat[0][i] = 1
        mat[i][0] = 1

    # Cycle on vertices 1 to n-1
    for i in range(1, n):
        j = 1 + (i % (n - 1))
        mat[i][j] = 1
        mat[j][i] = 1

    return mat
