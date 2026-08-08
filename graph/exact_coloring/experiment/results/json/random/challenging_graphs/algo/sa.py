#!/usr/bin/env python3
"""
Simulated Annealing for Graph Coloring.
Version optimisée avec matrice gamma.
"""

import random
import math

def _matrix_to_adj_list(adj_matrix):
    """Utilitaire de conversion si vous avez encore des matrices."""
    n = len(adj_matrix)
    adj_list = [[] for _ in range(n)]
    for u in range(n):
        for v in range(u + 1, n):
            if adj_matrix[u][v]:
                adj_list[u].append(v)
                adj_list[v].append(u)
    return adj_list


def _greedy_coloring(adj_list):
    """Coloration gloutonne en O(n + m)."""
    n = len(adj_list)
    colors = [-1] * n
    for u in range(n):
        used = {colors[v] for v in adj_list[u] if colors[v] != -1}
        c = 0
        while c in used:
            c += 1
        colors[u] = c
    return colors, max(colors) + 1 if colors else 0


def _sa_search(adj_list, k, max_iter, initial_temp, cooling_rate, min_temp, rng):
    """
    Cœur du Recuit Simulé.
    Évalue un mouvement en O(1) et met à jour la structure en O(deg(u)).
    """
    n = len(adj_list)
    if k <= 1:
        if all(len(neighbors) == 0 for neighbors in adj_list):
            return [0] * n, 0
        else:
            return [0] * n, sum(len(neighbors) for neighbors in adj_list) // 2

    # 1. Initialisation
    colors = [rng.randrange(k) for _ in range(n)]
    
    # gamma[u][c] = nombre de voisins de u colorés avec c
    gamma = [[0] * k for _ in range(n)]
    for u in range(n):
        cu = colors[u]
        for v in adj_list[u]:
            gamma[u][colors[v]] += 1

    # Calcul des conflits initiaux
    conflicts_set = set()
    total_conflicts = 0
    for u in range(n):
        if gamma[u][colors[u]] > 0:
            conflicts_set.add(u)
            total_conflicts += gamma[u][colors[u]]
    total_conflicts //= 2

    best_colors = colors[:]
    best_total_conflicts = total_conflicts

    if total_conflicts == 0:
        return best_colors, 0

    T = initial_temp
    
    # Convertir set en list pour un accès aléatoire O(1) rapide
    conflicts_list = list(conflicts_set)

    # 2. Boucle principale du Recuit
    for iteration in range(1, max_iter + 1):
        if total_conflicts == 0:
            break
            
        # Refroidissement
        if T > min_temp:
            T *= cooling_rate
        else:
            T = min_temp

        # Choisir un sommet aléatoire en conflit
        u = rng.choice(conflicts_list)
        old_c = colors[u]
        
        # Choisir une nouvelle couleur aléatoire
        available_c = [c for c in range(k) if c != old_c]
        new_c = rng.choice(available_c)

        # Delta E = variation du nombre de conflits
        delta_E = gamma[u][new_c] - gamma[u][old_c]

        # Critère d'acceptation de Metropolis
        accept = False
        if delta_E <= 0:
            accept = True
        else:
            # Probabilité d'accepter un mouvement dégradant
            prob = math.exp(-delta_E / T)
            if rng.random() < prob:
                accept = True

        if not accept:
            continue

        # 3. Appliquer le mouvement
        colors[u] = new_c
        total_conflicts += delta_E

        # Mise à jour de gamma et des conflits pour les voisins
        for v in adj_list[u]:
            gamma[v][old_c] -= 1
            gamma[v][new_c] += 1
            
            # Mettre à jour le statut de conflit du voisin v
            if gamma[v][colors[v]] == 0:
                if v in conflicts_set:
                    conflicts_set.discard(v)
            else:
                if v not in conflicts_set:
                    conflicts_set.add(v)

        # Mettre à jour le statut de u
        if gamma[u][new_c] == 0:
            conflicts_set.discard(u)
        else:
            conflicts_set.add(u)
            
        # Synchroniser la liste
        conflicts_list = list(conflicts_set)

        # 4. Sauvegarder le meilleur état
        if total_conflicts < best_total_conflicts:
            best_total_conflicts = total_conflicts
            best_colors = colors[:]
            if best_total_conflicts == 0:
                break

    return best_colors, best_total_conflicts


def sa_coloring(adj_matrix, max_iter=20000, initial_temp=10.0, cooling_rate=0.999, 
                min_temp=0.01, seed=None, verbose=False):
    """
    Colors the vertices of a graph using Simulated Annealing.
    Prend une matrice d'adjacence en entrée (comme les autres algorithmes).
    Essaie de réduire k itérativement comme pour Tabucol.
    """
    n = len(adj_matrix)
    if n == 0:
        return [], 0

    # Convertir la matrice d'adjacence en liste d'adjacence
    adj_list = _matrix_to_adj_list(adj_matrix)

    rng = random.Random(seed)
    best_colors, best_k = _greedy_coloring(adj_list)

    if verbose:
        print(f"  SA: starting from k = {best_k} (greedy upper bound)")

    current_k = best_k - 1
    while current_k >= 1:
        if verbose:
            print(f"  SA: trying k = {current_k}")

        colors, conflicts = _sa_search(adj_list, current_k, max_iter, 
                                       initial_temp, cooling_rate, min_temp, rng)

        if conflicts == 0:
            best_colors = colors
            best_k = current_k
            if verbose:
                print(f"  SA: found valid coloring with k = {current_k}")
            current_k -= 1
        else:
            if verbose:
                print(f"  SA: no valid coloring with k = {current_k}, stopping")
            break

    return best_colors, best_k


def sa_coloring_fixed_k(adj_list, k, max_iter=20000, initial_temp=10.0, 
                        cooling_rate=0.999, min_temp=0.01, seed=None, verbose=False):
    """
    SA variant that tries to find a valid coloring with a *fixed* number of colors k.
    """
    n = len(adj_list)
    if n == 0:
        return [], 0

    rng = random.Random(seed)
    return _sa_search(adj_list, k, max_iter, initial_temp, cooling_rate, min_temp, rng)