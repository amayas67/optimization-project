#!/usr/bin/env python3

import random


def random_greedy_coloring(adj_matrix, seed=None):
    """
    Colors the vertices of a graph using a greedy coloring on a
    random order of vertices.

    The order of vertices is randomly shuffled before applying the
    standard greedy coloring. The random order can be reproduced
    by setting the seed.

    Parameters
    ----------
    adj_matrix : list[list[int]]
        Symmetric n x n adjacency matrix, zero diagonal.
    seed : int, optional
        Seed for the random generator (reproducibility). Default: None.

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

    if seed is not None:
        random.seed(seed)

    order = list(range(n))
    random.shuffle(order)

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


def best_random_greedy_coloring(adj_matrix, trials=10, seed=None):
    """
    Runs multiple trials of random_greedy_coloring and returns the
    best coloring found (the one with the fewest colors).

    Parameters
    ----------
    adj_matrix : list[list[int]]
        Symmetric n x n adjacency matrix, zero diagonal.
    trials : int, optional
        Number of random trials. Default: 10.
    seed : int, optional
        Base seed for the trials (each trial uses seed + i).

    Returns
    -------
    colors : list[int]
        Best coloring found.
    nb_colors : int
        Corresponding number of colors.
    """
    best_colors = None
    best_nb = float('inf')

    for i in range(trials):
        s = seed + i if seed is not None else None
        colors, nb = random_greedy_coloring(adj_matrix, seed=s)
        if nb < best_nb:
            best_colors = colors
            best_nb = nb
            if best_nb == 0:
                break

    return best_colors, best_nb