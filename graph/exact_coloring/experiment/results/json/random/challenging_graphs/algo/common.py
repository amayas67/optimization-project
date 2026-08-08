#!/usr/bin/env python3

import random

def _matrix_to_adj_list(adj_matrix):
    n = len(adj_matrix)
    adj_list = [[] for _ in range(n)]
    for u in range(n):
        for v in range(u + 1, n):
            if adj_matrix[u][v]:
                adj_list[u].append(v)
                adj_list[v].append(u)
    return adj_list

def _adj_list_to_matrix(adj_list):
    n = len(adj_list)
    adj_matrix = [[0] * n for _ in range(n)]
    for u in range(n):
        for v in adj_list[u]:
            adj_matrix[u][v] = 1
    return adj_matrix

def _greedy_coloring(adj_list):
    n = len(adj_list)
    colors = [-1] * n
    for u in range(n):
        used = {colors[v] for v in adj_list[u] if colors[v] != -1}
        c = 0
        while c in used:
            c += 1
        colors[u] = c
    return colors, max(colors) + 1 if colors else 0

def _verify_coloring(adj_matrix, colors):
    n = len(adj_matrix)
    for u in range(n):
        for v in range(n):
            if adj_matrix[u][v] and colors[u] == colors[v]:
                return False
    return True