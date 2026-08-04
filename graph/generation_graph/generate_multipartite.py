#!/usr/bin/env python3

def generate_multipartite_adjacency_matrix(group_sizes):
    """
    Generates an adjacency matrix for a complete multipartite graph.

    Vertices are partitioned into k groups. An edge exists between two
    vertices if and only if they belong to different groups.
    There is never an edge within the same group.

    Parameters
    ----------
    group_sizes : list[int]
        List of the size of each group (e.g., [3, 2, 4] for 3 groups).

    Returns
    -------
    list[list[int]]
        Symmetric n x n adjacency matrix, zero diagonal,
        where n = sum(group_sizes).
    """
    n = sum(group_sizes)
    mat = [[0] * n for _ in range(n)]

    # Build the interval of each group
    intervals = []
    start = 0
    for size in group_sizes:
        intervals.append((start, start + size))
        start += size

    for a in range(n):
        # Find the group of vertex a
        group_a = next(i for i, (s, e) in enumerate(intervals) if s <= a < e)
        for b in range(a + 1, n):
            group_b = next(i for i, (s, e) in enumerate(intervals) if s <= b < e)
            if group_a != group_b:
                mat[a][b] = 1
                mat[b][a] = 1

    return mat
