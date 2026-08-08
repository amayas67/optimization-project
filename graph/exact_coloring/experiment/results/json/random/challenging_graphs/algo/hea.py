#!/usr/bin/env python3
"""
Hybrid Evolutionary Algorithm (HEA) for Graph Coloring.
Basé sur Galinier & Hao (1999). Combine Algorithme Génétique (GPX) et Tabu Search.
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


def _tabu_search_local(adj_list, k, colors, max_iter, rng):
    """
    Recherche Tabou pour raffiner une coloration (individu).
    Version intégrée pour le HEA.
    """
    n = len(adj_list)
    
    # Initialisation de gamma
    gamma = [[0] * k for _ in range(n)]
    for u in range(n):
        cu = colors[u]
        for v in adj_list[u]:
            gamma[u][colors[v]] += 1

    conflicts_set = set()
    total_conflicts = 0
    for u in range(n):
        if gamma[u][colors[u]] > 0:
            conflicts_set.add(u)
            total_conflicts += gamma[u][colors[u]]
    total_conflicts //= 2

    if total_conflicts == 0:
        return colors, 0

    tabu = [[0] * k for _ in range(n)]

    for iteration in range(1, max_iter + 1):
        if not conflicts_set:
            break

        best_move = None
        best_gain = -float('inf')

        for u in conflicts_set:
            old_c = colors[u]
            for new_c in range(k):
                if new_c == old_c:
                    continue
                gain = gamma[u][old_c] - gamma[u][new_c]
                is_tabu = tabu[u][new_c] > iteration
                if is_tabu and (total_conflicts - gain) >= total_conflicts:
                    continue
                if gain > best_gain:
                    best_gain = gain
                    best_move = (u, new_c, old_c)

        if best_move is None:
            if k <= 1:
                break
            u = rng.choice(list(conflicts_set))
            old_c = colors[u]
            available = [c for c in range(k) if c != old_c]
            if not available:
                break
            new_c = rng.choice(available)
            best_gain = gamma[u][old_c] - gamma[u][new_c]
            best_move = (u, new_c, old_c)

        u, new_c, old_c = best_move
        colors[u] = new_c
        total_conflicts -= best_gain

        for v in adj_list[u]:
            gamma[v][old_c] -= 1
            gamma[v][new_c] += 1
            if gamma[v][colors[v]] == 0: conflicts_set.discard(v)
            else: conflicts_set.add(v)

        if gamma[u][new_c] == 0: conflicts_set.discard(u)
        else: conflicts_set.add(u)

        tenure = int(0.6 * len(conflicts_set)) + rng.randint(0, 9)
        tabu[u][old_c] = iteration + tenure

    return colors, total_conflicts


def _gpx_crossover(parent1, parent2, k, rng):
    """
    Greedy Partition Crossover (GPX).
    Construit un enfant en assemblant les meilleures classes de couleur des parents.
    """
    n = len(parent1)
    child = [-1] * n
    
    # Transformer les parents en listes d'ensembles (les classes de couleur)
    p1_classes = [set() for _ in range(k)]
    p2_classes = [set() for _ in range(k)]
    for i in range(n):
        p1_classes[parent1[i]].add(i)
        p2_classes[parent2[i]].add(i)

    for c in range(k):
        # Choisir alternativement le parent 1 et le parent 2
        if c % 2 == 0:
            source_classes = p1_classes
            target_classes = p2_classes
        else:
            source_classes = p2_classes
            target_classes = p1_classes

        # Trouver la plus grande classe de couleur disponible
        max_size = -1
        best_class_idx = -1
        for i in range(k):
            if len(source_classes[i]) > max_size:
                max_size = len(source_classes[i])
                best_class_idx = i

        # Assigner cette classe à l'enfant
        chosen_vertices = source_classes[best_class_idx]
        for v in chosen_vertices:
            child[v] = c

        # Retirer ces sommets de l'autre parent pour garder la cohérence
        for i in range(k):
            target_classes[i].difference_update(chosen_vertices)
            
        # Vider la classe utilisée
        source_classes[best_class_idx].clear()

    # Les sommets restants (orphelins) prennent une couleur aléatoire
    for i in range(n):
        if child[i] == -1:
            child[i] = rng.randrange(k)

    return child


def _hea_search(adj_list, k, pop_size, max_generations, ls_iter, rng, verbose=False):
    """
    Cœur de l'Algorithme Évolutif Hybride.
    """
    n = len(adj_list)
    
    # 1. Initialisation de la population
    population = []
    for _ in range(pop_size):
        colors = [rng.randrange(k) for _ in range(n)]
        colors, conflicts = _tabu_search_local(adj_list, k, colors, ls_iter, rng)
        population.append((colors, conflicts))
        if conflicts == 0:
            return colors, 0

    # 2. Boucle Évolutive
    for gen in range(max_generations):
        # Sélection par tournoi binaire (2 parents)
        p1_idx = rng.randrange(pop_size)
        p2_idx = rng.randrange(pop_size)
        while p2_idx == p1_idx and pop_size > 1:
            p2_idx = rng.randrange(pop_size)
            
        parent1 = population[p1_idx][0]
        parent2 = population[p2_idx][0]

        # 3. Crossover (GPX)
        child_colors = _gpx_crossover(parent1, parent2, k, rng)

        # 4. Recherche Locale (Mutation/optimisation par Tabucol)
        child_colors, child_conflicts = _tabu_search_local(adj_list, k, child_colors, ls_iter, rng)

        if child_conflicts == 0:
            if verbose: print(f"  HEA: Solution parfaite trouvée à la génération {gen+1}")
            return child_colors, 0

        # 5. Remplacement (Stratégie de distance génétique)
        # Remplacer le parent auquel l'enfant ressemble le plus, si l'enfant est meilleur.
        # On mesure la ressemblance par le nombre de couleurs identiques.
        dist_p1 = sum(1 for i in range(n) if child_colors[i] == parent1[i])
        dist_p2 = sum(1 for i in range(n) if child_colors[i] == parent2[i])
        
        replace_idx = p1_idx if dist_p1 > dist_p2 else p2_idx
        
        if child_conflicts < population[replace_idx][1]:
            population[replace_idx] = (child_colors, child_conflicts)
            
        if verbose and gen % 10 == 0:
            best_conf = min(c for _, c in population)
            print(f"  HEA: Gen {gen} | Best Conflicts: {best_conf}")

    # Retourner le meilleur individu trouvé
    best_idx = min(range(pop_size), key=lambda i: population[i][1])
    return population[best_idx]


def hea_coloring(adj_matrix, pop_size=10, max_generations=50, ls_iter=1000, 
                 seed=None, verbose=False):
    """
    Colors the vertices of a graph using a Hybrid Evolutionary Algorithm.
    Prend une matrice d'adjacence en entrée (comme les autres algorithmes).
    """
    n = len(adj_matrix)
    if n == 0:
        return [], 0

    # Convertir la matrice d'adjacence en liste d'adjacence
    adj_list = _matrix_to_adj_list(adj_matrix)

    rng = random.Random(seed)
    best_colors, best_k = _greedy_coloring(adj_list)

    if verbose:
        print(f"  HEA: starting from k = {best_k} (greedy upper bound)")

    current_k = best_k - 1
    while current_k >= 1:
        if verbose:
            print(f"  HEA: trying k = {current_k}")

        colors, conflicts = _hea_search(adj_list, current_k, pop_size, 
                                        max_generations, ls_iter, rng, verbose)

        if conflicts == 0:
            best_colors = colors
            best_k = current_k
            if verbose:
                print(f"  HEA: found valid coloring with k = {current_k}")
            current_k -= 1
        else:
            if verbose:
                print(f"  HEA: no valid coloring with k = {current_k}, stopping")
            break

    return best_colors, best_k


def hea_coloring_fixed_k(adj_list, k, pop_size=10, max_generations=50, ls_iter=1000, 
                         seed=None, verbose=False):
    """
    HEA variant that tries to find a valid coloring with a *fixed* number of colors k.
    """
    n = len(adj_list)
    if n == 0:
        return [], 0

    rng = random.Random(seed)
    return _hea_search(adj_list, k, pop_size, max_generations, ls_iter, rng, verbose)