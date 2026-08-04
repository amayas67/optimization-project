#!/usr/bin/env python3

import random


def generate_tree_adjacency_matrix(n):
    """
    Generates an adjacency matrix for a random tree with n vertices.

    Uses the Prüfer sequence method: a random sequence of length n-2 is
    drawn, then converted into a tree (connected acyclic graph with n-1 edges).

    Parameters
    ----------
    n : int
        Number of vertices (n >= 1).

    Returns
    -------
    list[list[int]]
        Symmetric n x n adjacency matrix, zero diagonal.
    """
    if n <= 0:
        return []
    if n == 1:
        return [[0]]

    # Generate a random Prüfer sequence of length n-2
    prufer = [random.randint(0, n - 1) for _ in range(n - 2)]

    # Count the degree of each vertex
    degree = [1] * n
    for v in prufer:
        degree[v] += 1

    # Build the tree from the Prüfer sequence
    mat = [[0] * n for _ in range(n)]

    for v in prufer:
        for u in range(n):
            if degree[u] == 1:
                mat[v][u] = 1
                mat[u][v] = 1
                degree[v] -= 1
                degree[u] -= 1
                break

    # Last edge between the two remaining degree-1 vertices
    u = -1
    v = -1
    for i in range(n):
        if degree[i] == 1:
            if u == -1:
                u = i
            else:
                v = i
                break

    if v != -1:
        mat[u][v] = 1
        mat[v][u] = 1

    return mat
