#!/usr/bin/env python3
"""
Tabucol — Tabu Search for Graph Coloring (Hertz & de Werra, 1987).
Version optimisée.
"""

import random

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


def _tabu_search(adj_list, k, max_iter, rng):
    """
    Cœur du Tabucol optimisé.
    Utilise la matrice gamma pour évaluer les moves en O(1) et les appliquer en O(deg(u)).
    """
    n = len(adj_list)
    if k <= 1:
        # Cas trivial : k=1 n'est valide que s'il n'y a aucune arête
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
    total_conflicts //= 2  # Chaque arête en conflit est comptée deux fois

    best_colors = colors[:]
    best_total_conflicts = total_conflicts

    if total_conflicts == 0:
        return best_colors, 0

    # tabu[u][c] = itération jusqu'à laquelle il est interdit de colorer u avec c
    tabu = [[0] * k for _ in range(n)]

    # 2. Boucle de recherche Tabou
    for iteration in range(1, max_iter + 1):
        if not conflicts_set:
            break  # Solution valide trouvée

        best_move = None
        best_gain = -float('inf')

        # Évaluation de tous les moves (u, new_c) pour les sommets en conflit
        for u in conflicts_set:
            old_c = colors[u]
            for new_c in range(k):
                if new_c == old_c:
                    continue
                
                # Gain = conflits supprimés - conflits créés
                gain = gamma[u][old_c] - gamma[u][new_c]
                
                is_tabu = tabu[u][new_c] > iteration
                # Critère d'aspiration : autoriser si ça bat le meilleur absolu
                if is_tabu and (total_conflicts - gain) >= best_total_conflicts:
                    continue
                
                if gain > best_gain:
                    best_gain = gain
                    best_move = (u, new_c, old_c)

        # Si aucun move n'est possible (tous tabous et aucun n'aspire), 
        # on force un mouvement aléatoire pour débloquer la recherche
        if best_move is None:
            u = rng.choice(list(conflicts_set))
            old_c = colors[u]
            available_c = [c for c in range(k) if c != old_c]
            new_c = rng.choice(available_c)
            best_gain = gamma[u][old_c] - gamma[u][new_c]
            best_move = (u, new_c, old_c)

        u, new_c, old_c = best_move

        # 3. Appliquer le mouvement
        colors[u] = new_c
        total_conflicts -= best_gain

        # Mettre à jour gamma pour les voisins
        for v in adj_list[u]:
            gamma[v][old_c] -= 1
            gamma[v][new_c] += 1
            
            # Mettre à jour l'ensemble des sommets en conflit
            if gamma[v][colors[v]] == 0:
                conflicts_set.discard(v)
            else:
                conflicts_set.add(v)

        # Mettre à jour le statut de u
        if gamma[u][new_c] == 0:
            conflicts_set.discard(u)
        else:
            conflicts_set.add(u)

        # 4. Mettre à jour la liste taboue (Tenure dynamique)
        # L = floor(0.6 * |C|) + randint(0, 9)
        tenure = int(0.6 * len(conflicts_set)) + rng.randint(0, 9)
        # On interdit de revenir à old_c pour u
        tabu[u][old_c] = iteration + tenure

        # 5. Sauvegarder le meilleur état
        if total_conflicts < best_total_conflicts:
            best_total_conflicts = total_conflicts
            best_colors = colors[:]
            if best_total_conflicts == 0:
                break

    return best_colors, best_total_conflicts


def tabucol_coloring(adj_matrix, k=None, max_iter=10000, seed=None, verbose=False):
    """
    Colors the vertices of a graph using the Tabucol algorithm.
    Prend une matrice d'adjacence en entrée (comme les autres algorithmes).
    """
    n = len(adj_matrix)
    if n == 0:
        return [], 0

    # Convertir la matrice d'adjacence en liste d'adjacence
    adj_list = _matrix_to_adj_list(adj_matrix)
    
    rng = random.Random(seed)
    best_colors, best_k = _greedy_coloring(adj_list)

    if k is not None:
        best_k = min(k, best_k)

    if verbose:
        print(f"  Tabucol: starting from k = {best_k} (greedy upper bound)")

    current_k = best_k - 1
    while current_k >= 1:
        if verbose:
            print(f"  Tabucol: trying k = {current_k}")

        colors, conflicts = _tabu_search(adj_list, current_k, max_iter, rng)

        if conflicts == 0:
            best_colors = colors
            best_k = current_k
            if verbose:
                print(f"  Tabucol: found valid coloring with k = {current_k}")
            current_k -= 1
        else:
            if verbose:
                print(f"  Tabucol: no valid coloring with k = {current_k}, stopping")
            break

    return best_colors, best_k


def tabucol_coloring_fixed_k(adj_list, k, max_iter=10000, seed=None, verbose=False):
    """
    Tabucol variant that tries to find a valid coloring with a *fixed* number of colors k.
    """
    n = len(adj_list)
    if n == 0:
        return [], 0

    rng = random.Random(seed)
    return _tabu_search(adj_list, k, max_iter, rng)