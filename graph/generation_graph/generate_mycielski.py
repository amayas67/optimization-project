#!/usr/bin/env python3

def generate_mycielski_adjacency_matrix(k):
    """
    Generates an adjacency matrix for the Mycielski graph M_k.

    The Mycielski construction produces triangle-free graphs with
    increasing chromatic number. M_2 = K_2 (χ=2), M_3 = C_5 (χ=3),
    M_4 has χ=4, etc. M_k has χ = k.

    Construction: from a graph G with n vertices (v_0..v_{n-1}), we
    create M(G) with 2n+1 vertices:
      - v_0..v_{n-1}: copy of G
      - u_0..u_{n-1}: new vertices, u_i connected to the neighbors of v_i
      - w: central vertex connected to all u_i

    Parameters
    ----------
    k : int
        Index of the Mycielski graph (k ≥ 2, M_2 = K_2).

    Returns
    -------
    list[list[int]]
        Symmetric adjacency matrix, zero diagonal.
    """
    if k < 2:
        return []

    # M_2 = K_2
    mat = [[0, 1], [1, 0]]

    for _ in range(k - 2):
        n = len(mat)
        new_n = 2 * n + 1
        new_mat = [[0] * new_n for _ in range(new_n)]

        # Copy of G into v_0..v_{n-1}
        for i in range(n):
            for j in range(n):
                new_mat[i][j] = mat[i][j]

        # u_i (indices n..2n-1) connected to neighbors of v_i
        for i in range(n):
            for j in range(n):
                if mat[i][j] == 1:
                    new_mat[n + i][j] = 1
                    new_mat[j][n + i] = 1

        # w (index 2n) connected to all u_i
        for i in range(n):
            new_mat[2 * n][n + i] = 1
            new_mat[n + i][2 * n] = 1

        mat = new_mat

    return mat
