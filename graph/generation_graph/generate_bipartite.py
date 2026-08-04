#!/usr/bin/env python3

import random


def generate_bipartite_adjacency_matrix(u, v, p=0.5):
    """
    Generates an adjacency matrix for a random bipartite graph.

    Vertices are divided into two partitions:
      - U: indices 0 to u-1
      - V: indices u to u+v-1

    Edges exist only between a vertex in U and a vertex in V.
    No edges within U or within V.

    Parameters
    ----------
    u : int
        Number of vertices in the first partition.
    v : int
        Number of vertices in the second partition.
    p : float, optional
        Probability that an edge is present between U and V (between 0 and 1). Default: 0.5.

    Returns
    -------
    list[list[int]]
        Symmetric (u+v) x (u+v) adjacency matrix, zero diagonal.
    """
    n = u + v
    mat = [[0] * n for _ in range(n)]

    for i in range(u):
        for j in range(u, n):
            if random.random() < p:
                mat[i][j] = 1
                mat[j][i] = 1

    return mat
