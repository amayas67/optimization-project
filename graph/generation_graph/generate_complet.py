#!/usr/bin/env python3

def generate_complete_adjacency_matrix(n):
    """
    Generates an adjacency matrix for a complete graph K_n.

    All vertices are connected to each other (except self-loops).

    Parameters
    ----------
    n : int
        Number of vertices.

    Returns
    -------
    list[list[int]]
        n x n adjacency matrix: 1 everywhere except on the diagonal.
    """
    mat = [[1] * n for _ in range(n)]
    for i in range(n):
        mat[i][i] = 0
    return mat
