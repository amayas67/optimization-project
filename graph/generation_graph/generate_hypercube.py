#!/usr/bin/env python3

def generate_hypercube_adjacency_matrix(d):
    """
    Generates an adjacency matrix for a hypercube of dimension d.

    The hypercube Q_d has 2^d vertices, each labeled by a binary
    string of length d. Two vertices are connected if they differ
    in exactly one bit.
    χ = 2 (bipartite hypercube).

    Parameters
    ----------
    d : int
        Dimension of the hypercube (d ≥ 1).

    Returns
    -------
    list[list[int]]
        Symmetric 2^d x 2^d adjacency matrix, zero diagonal.
    """
    if d < 0:
        return []
    n = 1 << d  # 2^d
    if n == 0:
        return []

    mat = [[0] * n for _ in range(n)]

    for u in range(n):
        for bit in range(d):
            v = u ^ (1 << bit)  # Flip bit `bit`
            if v > u:  # Avoid duplicates
                mat[u][v] = 1
                mat[v][u] = 1

    return mat
