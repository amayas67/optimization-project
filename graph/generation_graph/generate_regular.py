#!/usr/bin/env python3

import random


def generate_regular_adjacency_matrix(n, d):
    """
    Generates an adjacency matrix for a random d-regular graph with n vertices.

    Uses the configuration model (random matching of half-edges).
    Each vertex receives d half-edges ("stubs"), then they are randomly paired.
    Self-loops and multiple edges are rejected (retry).

    Parameters
    ----------
    n : int
        Number of vertices (n >= 1).
    d : int
        Degree of each vertex (0 <= d < n). The product n*d must be even.

    Returns
    -------
    list[list[int]]
        Symmetric n x n adjacency matrix, zero diagonal, each vertex
        having degree d.
    """
    if n < 0:
        return []
    if n == 0:
        return []
    if d == 0:
        return [[0] * n for _ in range(n)]
    if d >= n:
        raise ValueError(
            f"Impossible: d={d} >= n={n}. "
            f"The degree must be strictly less than the number of vertices."
        )
    if n * d % 2 != 0:
        raise ValueError(
            f"Impossible: n*d = {n}*{d} = {n*d} is odd. "
            f"The product n*d must be even for a d-regular graph."
        )

    # Special case: complete graph (d = n-1)
    if d == n - 1:
        mat = [[1] * n for _ in range(n)]
        for i in range(n):
            mat[i][i] = 0
        return mat

    max_attempts = 1000
    for attempt in range(max_attempts):
        # Create the list of half-edges (stubs)
        stubs = []
        for i in range(n):
            stubs.extend([i] * d)

        random.shuffle(stubs)

        mat = [[0] * n for _ in range(n)]
        valid = True

        while stubs:
            u = stubs.pop()
            v = stubs.pop()

            if u == v or mat[u][v] == 1:
                # Self-loop or multiple edge → failure, retry
                valid = False
                break

            mat[u][v] = 1
            mat[v][u] = 1

        if valid:
            return mat

    raise RuntimeError(
        f"Failed to generate a {d}-regular graph with {n} vertices "
        f"after {max_attempts} attempts."
    )
