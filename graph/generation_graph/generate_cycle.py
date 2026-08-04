#!/usr/bin/env python3

def generate_cycle_adjacency_matrix(n):
    """
    Generates an adjacency matrix for a cycle C_n.

    Vertices are connected in a loop: 0-1-2-...-(n-1)-0.
    χ = 2 if n is even, 3 if n is odd (n ≥ 3).

    Parameters
    ----------
    n : int
        Number of vertices (n ≥ 3).

    Returns
    -------
    list[list[int]]
        Symmetric n x n adjacency matrix, zero diagonal.
    """
    if n < 0:
        return []
    if n <= 2:
        return [[0] * n for _ in range(n)]

    mat = [[0] * n for _ in range(n)]
    for i in range(n):
        j = (i + 1) % n
        mat[i][j] = 1
        mat[j][i] = 1
    return mat
