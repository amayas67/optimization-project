#!/usr/bin/env python3

def generate_grid_adjacency_matrix(rows, cols):
    """
    Generates an adjacency matrix for a 2D grid rows × cols.

    Vertices are arranged on a rectangular grid. Each vertex
    is connected to its horizontal and vertical neighbors (no diagonals).
    χ = 2 (bipartite grid).

    Parameters
    ----------
    rows : int
        Number of rows.
    cols : int
        Number of columns.

    Returns
    -------
    list[list[int]]
        Symmetric (rows*cols) x (rows*cols) adjacency matrix, zero diagonal.
    """
    n = rows * cols
    if n == 0:
        return []

    mat = [[0] * n for _ in range(n)]

    for r in range(rows):
        for c in range(cols):
            u = r * cols + c
            # Right neighbor
            if c + 1 < cols:
                v = r * cols + (c + 1)
                mat[u][v] = 1
                mat[v][u] = 1
            # Bottom neighbor
            if r + 1 < rows:
                v = (r + 1) * cols + c
                mat[u][v] = 1
                mat[v][u] = 1

    return mat
