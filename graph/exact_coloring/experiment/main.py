#!/usr/bin/env python3
"""
main.py — Comparison of coloring algorithms on the same graph.

Generates a graph of a chosen type, applies the nine portfolio algorithms,
displays terminal reports + interactive figures, then exports:
  • a "machine-ready" JSON in results/json/<type>/  (flat features,
    precomputed labels, raw matrix → ready for machine learning);

Usage:
    python main.py
"""

import json
import math
import os
import re
import sys
import time
import random
from datetime import datetime

# ===========================================================================
# Graph generators imports
# ===========================================================================
# Each generator returns an n×n adjacency matrix (list[list[int]]),
# symmetric, with zero diagonal. 1 = edge, 0 = no edge.
# ===========================================================================

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "generation_graph"))

from generate_complet import generate_complete_adjacency_matrix
from generate_bipartite import generate_bipartite_adjacency_matrix
from generate_graph_random import generate_random_adjacency_matrix
from generate_multipartite import generate_multipartite_adjacency_matrix
from generate_tree import generate_tree_adjacency_matrix
from generate_regular import generate_regular_adjacency_matrix
from generate_cycle import generate_cycle_adjacency_matrix
from generate_wheel import generate_wheel_adjacency_matrix
from generate_grid import generate_grid_adjacency_matrix
from generate_hypercube import generate_hypercube_adjacency_matrix
from generate_mycielski import generate_mycielski_adjacency_matrix

# ===========================================================================
# Coloring algorithms imports
# ===========================================================================
# Each algorithm takes an adjacency matrix and returns:
#   colors : list[int] — color of each vertex
#   nb_colors : int    — number of colors used
# ===========================================================================

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "algo"))

from greedy import greedy_coloring
from backtrack import backtrack_coloring
from dsatur import dsatur_coloring
from welsh_powell import welsh_powell_coloring
from smallest_degree_last import smallest_degree_last_coloring
from random_greedy import random_greedy_coloring, best_random_greedy_coloring
from rlf import rlf_coloring
from ido import ido_coloring
from tabu import tabucol_coloring
from sa import sa_coloring
from hea import hea_coloring

# ===========================================================================
# Matplotlib display
# ===========================================================================

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch, Circle

THEME = {
    "background": "#0E1621", "title": "#EAF2F7", "text": "#93A9B8", "muted": "#5D7284",
    "edge": "#3A4E60", "edge_hi": "#A8DFF0", "frame": "#2C4054", "panel": "#16222F",
}

PALETTE = [
    "#F5A83C", "#2FBFAE", "#EE7FA9", "#7B9CF5",
    "#A3D65C", "#F0795B", "#5AC8E8", "#C88BE0",
    "#E8C547", "#63D6B1", "#D98AD9", "#8FB8FF",
]


def _to_hex(c):
    if isinstance(c, str):
        return c
    r, g, b = (int(round(v * 255)) for v in c[:3])
    return f"#{r:02x}{g:02x}{b:02x}"


def _palette(nb):
    if nb <= len(PALETTE):
        return PALETTE[:nb]
    cmap = plt.get_cmap("tab20", nb)
    return [_to_hex(cmap(i)) for i in range(nb)]


def _shade(hexcolor, factor=0.66):
    r, g, b = (int(hexcolor[i:i + 2], 16) for i in (1, 3, 5))
    return f"#{int(r * factor):02x}{int(g * factor):02x}{int(b * factor):02x}"


def _label_color(hexcolor):
    r, g, b = (int(hexcolor[i:i + 2], 16) / 255 for i in (1, 3, 5))
    luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return "#0F1822" if luminance > 0.6 else "#F4F8FB"


def _circle_layout(n):
    if n == 1:
        return [(0.0, 0.0)]
    return [(math.cos(2 * math.pi * i / n - math.pi / 2),
             math.sin(2 * math.pi * i / n - math.pi / 2)) for i in range(n)]


def _spring_layout(adj, iterations=160, seed=42):
    n = len(adj)
    if n <= 1:
        return _circle_layout(n)
    rng = random.Random(seed)
    pos = [[rng.uniform(-1, 1), rng.uniform(-1, 1)] for _ in range(n)]
    k = 2.0 / math.sqrt(n)
    temp = 0.4
    for _ in range(iterations):
        disp = [[0.0, 0.0] for _ in range(n)]
        for i in range(n):
            xi, yi = pos[i]
            for j in range(i + 1, n):
                dx, dy = xi - pos[j][0], yi - pos[j][1]
                d = math.hypot(dx, dy) or 1e-4
                ux, uy = dx / d, dy / d
                f_rep = k * k / d
                disp[i][0] += ux * f_rep; disp[i][1] += uy * f_rep
                disp[j][0] -= ux * f_rep; disp[j][1] -= uy * f_rep
                if adj[i][j]:
                    f_att = d * d / k
                    disp[i][0] -= ux * f_att; disp[i][1] -= uy * f_att
                    disp[j][0] += ux * f_att; disp[j][1] += uy * f_att
        for i in range(n):
            d = math.hypot(disp[i][0], disp[i][1])
            if d > 1e-9:
                s = min(d, temp) / d
                pos[i][0] += disp[i][0] * s
                pos[i][1] += disp[i][1] * s
        temp *= 0.965
    cx = sum(p[0] for p in pos) / n
    cy = sum(p[1] for p in pos) / n
    pos = [[p[0] - cx, p[1] - cy] for p in pos]
    rmax = max(math.hypot(x, y) for x, y in pos) or 1.0
    return [(x / rmax, y / rmax) for x, y in pos]


def draw_graph(adj_matrix, colors, title="Graph Coloring",
               layout="circle", show=True, elapsed_ms=None):
    """Displays the colored graph (dark theme). Hover for neighborhood info; 's' to save PNG."""
    n = len(adj_matrix)
    if n == 0:
        print("Empty graph, nothing to display.")
        return None

    pos = _circle_layout(n) if layout == "circle" else _spring_layout(adj_matrix)
    deg = [sum(adj_matrix[i]) for i in range(n)]
    m = sum(deg) // 2
    delta = max(deg)
    used = sorted(set(colors))
    indice = {c: k for k, c in enumerate(used)}
    nb_colors = len(used)
    palette = _palette(nb_colors)
    counts = [colors.count(c) for c in used]

    fig, ax = plt.subplots(figsize=(9, 8.4))
    fig.patch.set_facecolor(THEME["background"])
    ax.set_facecolor(THEME["background"])
    try:
        fig.canvas.manager.set_window_title(title)
    except Exception:
        pass

    if layout == "circle" and n > 2:
        ax.add_patch(Circle((0, 0), 1.0, fill=False, color="#1D2C3A",
                            linestyle=(0, (3, 7)), linewidth=1.0, zorder=0.5))

    edges = []
    for i in range(n):
        for j in range(i + 1, n):
            if adj_matrix[i][j] == 1:
                p = FancyArrowPatch(pos[i], pos[j], arrowstyle="-",
                                    connectionstyle="arc3,rad=0.12",
                                    color=THEME["edge"], linewidth=1.1, alpha=0.85, zorder=1)
                ax.add_patch(p)
                edges.append((p, i, j))

    node_r = max(0.028, min(0.062, 1.6 / n))
    label_fs = 10.5 if node_r > 0.045 else 8.0
    nodes = []
    for i in range(n):
        c = palette[indice[colors[i]]]
        glow = Circle(pos[i], node_r * 1.7, facecolor=c, edgecolor="none", alpha=0.14, zorder=2)
        disc = Circle(pos[i], node_r, facecolor=c, edgecolor=_shade(c), linewidth=1.6, zorder=3)
        lab = ax.text(pos[i][0], pos[i][1], str(i), ha="center", va="center",
                      fontsize=label_fs, fontweight="bold", color=_label_color(c), zorder=4)
        ax.add_patch(glow); ax.add_patch(disc)
        nodes.append({"glow": glow, "node": disc, "label": lab, "ec": _shade(c)})

    panel = f"n    {n} vertices\nm    {m} edges\nχ̂    {nb_colors} colors\nΔ    {delta}"
    if elapsed_ms is not None:
        panel += f"\nt    {elapsed_ms:.2f} ms"
    ax.text(0.02, 0.98, panel, transform=ax.transAxes, va="top", ha="left",
            fontfamily="monospace", fontsize=9.5, color=THEME["text"], linespacing=1.55,
            bbox=dict(boxstyle="round,pad=0.6", facecolor=THEME["panel"],
                      edgecolor=THEME["frame"], alpha=0.92))

    handles = [mpatches.Patch(facecolor=palette[k], edgecolor="none",
               label=f"Color {c}  ·  {counts[k]} vertex{'es' if counts[k] > 1 else ''}")
               for k, c in enumerate(used)]
    leg = ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.02, 1.0),
                    frameon=True, fancybox=True, framealpha=0.92,
                    facecolor=THEME["panel"], edgecolor=THEME["frame"],
                    labelcolor="#D7E3EB", fontsize=9.5, title="Coloring", title_fontsize=10)
    leg.get_title().set_color(THEME["title"])

    ax.set_title(title, fontsize=15.5, fontweight="bold", color=THEME["title"], pad=20)
    ax.text(0.5, -0.015,
            "hover a node to highlight its neighborhood   ·   's' to save PNG   ·   press Enter for next figure",
            transform=ax.transAxes, ha="center", fontsize=8.5, color=THEME["muted"])
    ax.set_aspect("equal"); ax.axis("off")
    margin = max(math.hypot(x, y) for x, y in pos) + 0.35
    ax.set_xlim(-margin, margin); ax.set_ylim(-margin, margin)

    tip = ax.annotate("", xy=(0, 0), xytext=(14, 14), textcoords="offset points",
                      fontfamily="monospace", fontsize=9, color="#DCE9F1",
                      bbox=dict(boxstyle="round,pad=0.45", facecolor=THEME["panel"],
                                edgecolor="#35506A", alpha=0.95),
                      arrowprops=dict(arrowstyle="-", color="#35506A", lw=0.8), zorder=6)
    tip.set_visible(False)
    state = {"h": -1}

    def apply_effect(h):
        for i, a in enumerate(nodes):
            if h == -1:
                a["glow"].set_alpha(0.14); a["node"].set_alpha(1.0); a["label"].set_alpha(1.0)
                a["node"].set_edgecolor(a["ec"]); a["node"].set_linewidth(1.6)
            else:
                neighbor = (i == h) or adj_matrix[h][i]
                a["glow"].set_alpha(0.24 if i == h else (0.14 if neighbor else 0.03))
                a["node"].set_alpha(1.0 if neighbor else 0.18)
                a["label"].set_alpha(1.0 if neighbor else 0.18)
                a["node"].set_edgecolor("#EAF6FF" if i == h else a["ec"])
                a["node"].set_linewidth(2.4 if i == h else 1.6)
        for p, i, j in edges:
            if h == -1:
                p.set_color(THEME["edge"]); p.set_linewidth(1.1); p.set_alpha(0.85)
            elif h in (i, j):
                p.set_color(THEME["edge_hi"]); p.set_linewidth(2.3); p.set_alpha(1.0)
            else:
                p.set_color(THEME["edge"]); p.set_linewidth(1.1); p.set_alpha(0.08)

    def on_move(event):
        if event.inaxes != ax or event.xdata is None:
            target = -1
        else:
            target, best = -1, node_r * 1.9
            for i, (x, y) in enumerate(pos):
                d = math.hypot(event.xdata - x, event.ydata - y)
                if d < best:
                    target, best = i, d
        if target == state["h"]:
            return
        state["h"] = target
        apply_effect(target)
        if target == -1:
            tip.set_visible(False)
        else:
            neighbors = [j for j in range(n) if adj_matrix[target][j]]
            tip.xy = pos[target]
            tip.set_text(f"vertex {target} · degree {deg[target]}\n"
                         f"neighbors: {', '.join(map(str, neighbors)) if neighbors else '—'}")
            tip.set_visible(True)
        fig.canvas.draw_idle()

    def on_key(event):
        if event.key == "s":
            name = re.sub(r"[^\w\s-]+", "_", title, flags=re.I).strip("_")
            fig.savefig(f"{name}.png", dpi=200, bbox_inches="tight", facecolor=fig.get_facecolor())
            print(f"Figure saved: {name}.png")
        elif event.key == "enter":
            plt.close(fig)

    fig.canvas.mpl_connect("motion_notify_event", on_move)
    fig.canvas.mpl_connect("axes_leave_event", lambda e: on_move(e))
    fig.canvas.mpl_connect("key_press_event", on_key)

    plt.tight_layout()
    if show:
        plt.show()
    return fig, ax


# ---------------------------------------------------------------------------
# Terminal report
# ---------------------------------------------------------------------------

def _swatch(hexcolor):
    if not sys.stdout.isatty():
        return "⬤"
    r, g, b = (int(hexcolor[i:i + 2], 16) for i in (1, 3, 5))
    return f"\033[38;2;{r};{g};{b}m⬤\033[0m"


def print_report(algo, adj, colors, nb_colors, elapsed_ms=None):
    n = len(adj)
    m = sum(adj[i][j] for i in range(n) for j in range(i + 1, n))
    delta = max((sum(row) for row in adj), default=0)
    used = sorted(set(colors))
    palette = _palette(len(used))
    print(f"┌─ {algo} " + "─" * max(0, 42 - len(algo)))
    print(f"│ vertices  {n:<8} edges    {m}")
    print(f"│ colors    {nb_colors:<8} Δ        {delta}")
    if elapsed_ms is not None:
        print(f"│ time      {elapsed_ms:.2f} ms")
    print("│ palette   " + "  ".join(
        f"{_swatch(palette[k])}×{colors.count(c)}" for k, c in enumerate(used)))
    sol = str(colors)
    print(f"│ solution  {sol if len(sol) <= 46 else sol[:43] + '...'}")
    print("└" + "─" * 44)


# ---------------------------------------------------------------------------
# Graph characterization — "machine-ready" features (snake_case keys)
# ---------------------------------------------------------------------------

def _is_bipartite(adj):
    n = len(adj)
    color = [-1] * n
    for start in range(n):
        if color[start] != -1:
            continue
        color[start] = 0
        queue = [start]
        while queue:
            u = queue.pop()
            for v in range(n):
                if adj[u][v] == 1:
                    if color[v] == -1:
                        color[v] = 1 - color[u]
                        queue.append(v)
                    elif color[v] == color[u]:
                        return False
    return True


def _connected_components(adj):
    n = len(adj)
    seen = [False] * n
    nb = 0
    for start in range(n):
        if seen[start]:
            continue
        nb += 1
        stack = [start]
        seen[start] = True
        while stack:
            u = stack.pop()
            for v in range(n):
                if adj[u][v] == 1 and not seen[v]:
                    seen[v] = True
                    stack.append(v)
    return nb


def _girth(adj):
    n = len(adj)
    best = float("inf")
    for s in range(n):
        dist = [-1] * n
        parent = [-1] * n
        dist[s] = 0
        queue = [s]
        while queue:
            u = queue.pop(0)
            for v in range(n):
                if adj[u][v] != 1:
                    continue
                if dist[v] == -1:
                    dist[v] = dist[u] + 1
                    parent[v] = u
                    queue.append(v)
                elif parent[u] != v and parent[v] != u:
                    best = min(best, dist[u] + dist[v] + 1)
    return best if best != float("inf") else None


def _omega_lower_bound(adj):
    n = len(adj)
    order = sorted(range(n), key=lambda i: sum(adj[i]), reverse=True)
    clique = []
    for u in order:
        if all(adj[u][v] == 1 for v in clique):
            clique.append(u)
    return len(clique)


def graph_features(adj):
    """
    Flat structural features, ready for ML (snake_case keys,
    numeric or boolean values). `degree_sequence` is kept for
    advanced usage (excluded from the DataFrame by the loader).
    """
    n = len(adj)
    degrees = [sum(row) for row in adj]
    m = sum(degrees) // 2
    density = (2 * m / (n * (n - 1))) if n > 1 else 0.0
    avg_degree = (2 * m / n) if n else 0.0
    variance = (sum((d - avg_degree) ** 2 for d in degrees) / n) if n else 0.0
    return {
        "n": n,
        "m": m,
        "density": round(density, 6),
        "avg_degree": round(avg_degree, 4),
        "degree_std": round(math.sqrt(variance), 4),
        "delta_max": max(degrees) if degrees else 0,
        "delta_min": min(degrees) if degrees else 0,
        "bipartite": _is_bipartite(adj),
        "connected_components": _connected_components(adj),
        "girth": _girth(adj),                 # None if acyclic
        "omega_lower_bound": _omega_lower_bound(adj),
        "degree_sequence": degrees,
    }


def compute_labels(resultats, chi):
    """
    Labels for learning:
      best_algorithm = fewest colors, then lowest time;
      optimal_algorithms = all that reach χ.
    """
    best = min(resultats, key=lambda r: (r["n_colors"], r["time_ms"]))
    optimal = [r["algorithm"] for r in resultats if r["n_colors"] == chi]
    return {
        "best_algorithm": best["algorithm"],
        "best_n_colors": best["n_colors"],
        "optimal_algorithms": optimal,
        "n_optimal_algorithms": len(optimal),
    }


# ---------------------------------------------------------------------------
# Sequential file naming
# ---------------------------------------------------------------------------

def _next_sequence_index(directory, extension):
    """
    Returns the next sequential index for a file in `directory`.

    Scans existing files matching `*.{extension}` and returns the highest
    numeric prefix + 1. If the directory is empty, returns 1.
    """
    os.makedirs(directory, exist_ok=True)
    max_idx = 0
    for filename in os.listdir(directory):
        if not filename.endswith(f".{extension}"):
            continue
        stem = filename[: -len(extension) - 1]  # remove ".ext"
        if stem.isdigit():
            max_idx = max(max_idx, int(stem))
    return max_idx + 1


# ---------------------------------------------------------------------------
# JSON export — "machine-ready" format
# ---------------------------------------------------------------------------

def export_json(graph_type, params, adj, feats, resultats, chi, labels, seed, seq_index,
                chi_source="backtracking"):
    """
    Saves a self-descriptive sample in results/json/<type>/.

    Structure designed for ML:
      features      → X (flat feature vector)
      labels        → y (best_algorithm for classification)
      results       → per-algorithm details (gap, optimality, time, solution)
      instance      → reproducible raw data (matrix + seed)
    """
    folder = os.path.join(os.path.dirname(__file__), "results", "json", graph_type)
    os.makedirs(folder, exist_ok=True)
    run_id = f"{seq_index:06d}"
    path = os.path.join(folder, f"{run_id}.json")

    data = {
        "schema_version": "1.0",
        "run_id": run_id,
        "generated_at": datetime.now().isoformat(),
        "seed": seed,
        "instance": {
            "type": graph_type,
            "params": params,
            "n_vertices": feats["n"],
            "n_edges": feats["m"],
            "adjacency_matrix": adj,
        },
        "features": feats,
        "ground_truth": {"chi": chi, "source": chi_source},
        "results": resultats,
        "labels": labels,
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✓ JSON (machine): {path}")
    return path


# ---------------------------------------------------------------------------
# ML loader: results/json/** → pandas DataFrame
# ---------------------------------------------------------------------------

def load_data(root=None, format="long"):
    """
    Aggregates all JSON files from results/json/ into a pandas DataFrame.

    format="long": one row per (instance, algorithm)
                   → X = features, y = optimal / n_colors / gap_to_chi.
    format="wide": one row per instance
                   → X = features, y = labels.best_algorithm.
    """
    try:
        import pandas as pd
    except ImportError:
        print("pandas is required to load the corpus: pip install pandas")
        return None

    if root is None:
        root = os.path.join(os.path.dirname(__file__), "results", "json")

    rows = []
    for type_dir in sorted(os.listdir(root)):
        dir_path = os.path.join(root, type_dir)
        if not os.path.isdir(dir_path):
            continue
        for filename in sorted(os.listdir(dir_path)):
            if not filename.endswith(".json"):
                continue
            with open(os.path.join(dir_path, filename), encoding="utf-8") as f:
                d = json.load(f)
            base = {"run_id": d["run_id"], "type": d["instance"]["type"],
                    "chi": d["ground_truth"]["chi"]}
            base.update({k: v for k, v in d["features"].items() if k != "degree_sequence"})
            if format == "wide":
                base["best_algorithm"] = d["labels"]["best_algorithm"]
                base["best_n_colors"] = d["labels"]["best_n_colors"]
                base["n_optimal_algorithms"] = d["labels"]["n_optimal_algorithms"]
                rows.append(base)
            else:
                for r in d["results"]:
                    row = dict(base)
                    row.update({"algorithm": r["algorithm"], "n_colors": r["n_colors"],
                                "gap_to_chi": r["gap_to_chi"], "optimal": r["optimal"],
                                "time_ms": r["time_ms"]})
                    rows.append(row)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Demonstration: generation, comparison, exports
# ---------------------------------------------------------------------------

if __name__ == "__main__":

    # === Configuration =====================================================
    show = False        # False → no matplotlib window
    layout = "circle"    # "circle" or "spring"
    SEED = None          # fix an integer (e.g. 42) for a reproducible corpus
    loop_nb = 296    # number of graphs to generate and color in a row

    # Graph type to generate — choose a number:
    #   1  → random       (Erdős–Rényi G(n, p))
    #   2  → bipartite    (random bipartite graph)
    #   3  → complete     (complete graph K_n)
    #   4  → multipartite (complete k-partite graph)
    #   5  → tree         (random tree via Prüfer)
    #   6  → regular      (random d-regular graph)
    #   7  → cycle        (cycle C_n)
    #   8  → wheel        (wheel W_n)
    #   9  → grid         (2D grid rows × cols)
    #   10 → hypercube    (hypercube Q_d)
    #   11 → mycielski    (Mycielski graph M_k, triangle-free, χ = k)
    generate = 1  # you can modify this value to choose another graph

    GENERATORS = {
        1: "random", 2: "bipartite", 3: "complete", 4: "multipartite",
        5: "tree", 6: "regular", 7: "cycle", 8: "wheel",
        9: "grid", 10: "hypercube", 11: "mycielski",
    }
    GRAPH_TYPE = GENERATORS[generate]

    # Parameters for each graph type (modify as needed):
    #   random       → n: number of vertices, p: edge probability (0 ≤ p ≤ 1)
    #                  m: exact number of edges (optionnel, remplace p si fourni).
    #                  Condition : 0 ≤ m ≤ n*(n-1)/2 (max arêtes d'un graphe simple).
    #   bipartite    → u: partition U vertices, v: partition V vertices, p: U–V edge probability
    #   complete     → n: number of vertices (χ = n)
    #   multipartite → group_sizes: list of each group's size (ex: [2, 2, 2] → χ = 3)
    #   tree         → n: number of vertices (χ = 2 if n ≥ 2)
    #   regular      → n: number of vertices, d: degree of each vertex (n×d must be even)
    #   cycle        → n: number of vertices (χ = 2 if n even, 3 if n odd)
    #   wheel        → n: total number of vertices, vertex 0 = center (χ = 3 or 4)
    #   grid         → rows: number of rows, cols: number of columns (χ = 2)
    #   hypercube    → d: dimension (2^d vertices, χ = 2)
    #   mycielski    → k: index (M_k has χ = k, triangle-free; M_2 = K_2, M_3 = C_5)
    PARAMS = {
        "random":       {"n": 50, "p": 0.6},   #p means edge probability or  you can choose t il manully by replacing p with m the exact number of edges
        "bipartite":    {"u": 5, "v": 5, "p": 0.5},
        "complete":     {"n": 8},
        "multipartite": {"group_sizes": [2, 2, 2]},
        "tree":         {"n": 16},
        "regular":      {"n": 10, "d": 3},
        "cycle":        {"n": 10},
        "wheel":        {"n": 10},
        "grid":         {"rows": 3, "cols": 4},
        "hypercube":    {"d": 3},
        "mycielski":    {"k": 4},
    }

    # (machine_id, display_name, function)
    ALGORITHMS = [
        ("greedy",               "Greedy",               lambda g: greedy_coloring(g)),
        ("welsh_powell",         "Welsh-Powell",         lambda g: welsh_powell_coloring(g)),
        ("dsatur",               "DSATUR",               lambda g: dsatur_coloring(g)),
        ("ido",                  "IDO",                  lambda g: ido_coloring(g)),
        ("rlf",                  "RLF",                  lambda g: rlf_coloring(g)),
        ("smallest_degree_last", "Smallest-degree-last", lambda g: smallest_degree_last_coloring(g)),
        ("random_greedy",        "Random greedy (×10)",  lambda g: best_random_greedy_coloring(g, trials=10)),
        ("sa",                   "Simulated Annealing",  lambda g: sa_coloring(g, max_iter=20000)),
        ("hea",                  "Hybrid Evolutionary",  lambda g: hea_coloring(g, pop_size=10, max_generations=50, ls_iter=1000)),
        ("tabu",                 "Tabucol",              lambda g: tabucol_coloring(g, max_iter=1000)),
        ("backtracking",         "Backtracking (exact)", lambda g: backtrack_coloring(g)),
    ]
    NAMES = {a: n for a, n, _ in ALGORITHMS}

    # === Generation ========================================================
    params = PARAMS[GRAPH_TYPE]
    generators = {
        "random":       lambda p: generate_random_adjacency_matrix(**p),
        "bipartite":    lambda p: generate_bipartite_adjacency_matrix(**p),
        "complete":     lambda p: generate_complete_adjacency_matrix(**p),
        "multipartite": lambda p: generate_multipartite_adjacency_matrix(**p),
        "tree":         lambda p: generate_tree_adjacency_matrix(**p),
        "regular":      lambda p: generate_regular_adjacency_matrix(**p),
        "cycle":        lambda p: generate_cycle_adjacency_matrix(**p),
        "wheel":        lambda p: generate_wheel_adjacency_matrix(**p),
        "grid":         lambda p: generate_grid_adjacency_matrix(**p),
        "hypercube":    lambda p: generate_hypercube_adjacency_matrix(**p),
        "mycielski":    lambda p: generate_mycielski_adjacency_matrix(**p),
    }

    for loop_idx in range(loop_nb):
        print(f"\n{'#' * 64}")
        print(f"#  Generation {loop_idx + 1} / {loop_nb}  —  {GRAPH_TYPE}")
        print(f"{'#' * 64}\n")

        # Seed: offset by loop index so each graph differs yet stays reproducible
        current_seed = SEED + loop_idx if SEED is not None else None
        if current_seed is not None:
            random.seed(current_seed)

        adj = generators[GRAPH_TYPE](params)
        n = len(adj)
        feats = graph_features(adj)

        # === Comparison loop ===================================================
        results = []
        for algo_id, name, algo in ALGORITHMS:
            t0 = time.perf_counter()
            colors, nb_colors = algo(adj)
            dt = (time.perf_counter() - t0) * 1000

            print_report(f"{name} ({GRAPH_TYPE}, n={n})", adj, colors, nb_colors, dt)
            print()

            if show:
                draw_graph(adj, colors,
                           title=f"{name} — {nb_colors} color{'s' if nb_colors > 1 else ''}",
                           layout=layout, show=True, elapsed_ms=dt)

            results.append({
                "algorithm": algo_id,
                "n_colors": nb_colors,
                "gap_to_chi": None,          # filled after χ calculation
                "optimal": None,
                "time_ms": round(dt, 3),
                "solution": colors,
            })

        # χ = result from backtracking (exact algorithm) if present,
        # otherwise fallback to the best heuristic result.
        bt = next((r for r in results if r["algorithm"] == "backtracking"), None)
        if bt is not None:
            chi = bt["n_colors"]
            chi_source = "backtracking"
        else:
            chi = min(r["n_colors"] for r in results)
            chi_source = "best_heuristic"
        for r in results:
            r["gap_to_chi"] = r["n_colors"] - chi
            r["optimal"] = (r["n_colors"] == chi)
        labels = compute_labels(results, chi)

        # === Terminal summary ==================================================
        print("=" * 64)
        print(f"  {'Algorithm':<25} {'Colors':>8} {'Gap':>6} {'Optimal':>8} {'ms':>11}")
        print("-" * 64)
        for r in results:
            ok = "✓" if r["optimal"] else "✗"
            print(f"  {NAMES[r['algorithm']]:<25} {r['n_colors']:>8} "
                  f"{r['gap_to_chi']:>+6} {ok:>8} {r['time_ms']:>11.2f}")
        print("=" * 64)
        print(f"  χ = {chi}   ·   best: {NAMES[labels['best_algorithm']]}")
        print()

        # === Exports ===========================================================
        json_dir = os.path.join(os.path.dirname(__file__), "results", "json", GRAPH_TYPE)
        seq_index = _next_sequence_index(json_dir, "json")
        export_json(GRAPH_TYPE, params, adj, feats, results, chi, labels, current_seed, seq_index,
                    chi_source)

    # For later aggregation: df = load_data()  (format="long" or "wide")
