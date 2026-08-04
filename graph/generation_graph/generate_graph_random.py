#!/usr/bin/env python3

import random


def generate_random_adjacency_matrix(n, p=0.5, m=None):
    """
    Generates a random adjacency matrix.

    Parameters
    ----------
    n : int
        Number of vertices.
    p : float, optional
        Probability that an edge is present (between 0 and 1). Default: 0.5.
    m : int, optional
        Exact number of edges to include. If provided, overrides `p` and the
        graph will have exactly `m` edges chosen at random.

    Returns
    -------
    list[list[int]]
        Symmetric n x n adjacency matrix, zero diagonal.
    """
    mat = [[0] * n for _ in range(n)]

    if m is not None:
        max_edges = n * (n - 1) // 2
        if m > max_edges:
            raise ValueError(
                f"Cannot have {m} edges in a simple graph with {n} vertices "
                f"(max possible: {max_edges})"
            )
        # Générer toutes les paires possibles
        pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
        chosen = random.sample(pairs, m)
        for i, j in chosen:
            mat[i][j] = 1
            mat[j][i] = 1
    else:
        for i in range(n):
            for j in range(i + 1, n):
                if random.random() < p:
                    mat[i][j] = 1
                    mat[j][i] = 1

    return mat
