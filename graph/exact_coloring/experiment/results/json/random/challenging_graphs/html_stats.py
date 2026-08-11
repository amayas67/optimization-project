#!/usr/bin/env python3
"""
html_stats.py — Analyse the JSON files in the current directory and produces
an interactive `stats.html` page.

Corrected version:
- run_id is always the JSON filename without extension.
- Bash exports are safe for filenames containing spaces, parentheses, quotes.
- HTML chips are escaped.
- Added n_colors and gap_to_chi for each instance in the detail view and union view.
- Fixed union gap logic: gap/color now reflect the best selected algorithm(s),
  not necessarily the global best algorithm.
- Gap is recomputed from chi when possible, instead of blindly trusting JSON.
- JSON keys/values are normalized to tolerate trailing spaces.
"""

import html as html_mod
import json
import os
import sys
from collections import defaultdict
from datetime import datetime


# ---------------------------------------------------------------------------
# Ordre d'affichage des algorithmes (noms d'affichage → nom JSON)
# ---------------------------------------------------------------------------

ALGORITHMS = [
    ("Greedy", "greedy"),
    ("Welsh-Powell", "welsh_powell"),
    ("DSATUR", "dsatur"),
    ("IDO", "ido"),
    ("RLF", "rlf"),
    ("Smallest-degree-last", "smallest_degree_last"),
    ("Random greedy (×10)", "random_greedy"),
    ("Simulated Annealing", "sa"),
    ("Hybrid Evolutionary", "hea"),
    ("Tabucol", "tabu"),
    ("Backtracking (exact)", "backtracking"),
    ("CP-SAT (OR-Tools)", "cpsat"),
    ("SAT", "sat"),
]

# Noms JSON des 10 premiers algorithmes du portfolio (pour "The first ten").
FIRST_TEN_ALGOS = [
    "greedy",
    "welsh_powell",
    "dsatur",
    "ido",
    "rlf",
    "smallest_degree_last",
    "random_greedy",
    "sa",
    "hea",
    "tabu",
]

# Catégories de densité
DENSITY_CATEGORIES = [
    ("Very dense", 0.75, 1.01),
    ("Dense", 0.50, 0.75),
    ("Moderately dense", 0.25, 0.50),
    ("Sparse", 0.10, 0.25),
    ("Very sparse", 0.00, 0.10),
]

# Catégories de taille (nombre de sommets)
SIZE_CATEGORIES = [
    ("1–25 vertices", 1, 25),
    ("26–50 vertices", 26, 50),
    ("51–100 vertices", 51, 100),
    ("101–200 vertices", 101, 200),
    ("201+ vertices", 201, 999999),
]


def _density_category(density):
    """Retourne le nom de la catégorie de densité."""
    for name, lo, hi in DENSITY_CATEGORIES:
        if lo <= density < hi:
            return name
    return "Very sparse"


def _size_category(n_vertices):
    """Retourne le nom de la catégorie de taille."""
    for name, lo, hi in SIZE_CATEGORIES:
        if lo <= n_vertices <= hi:
            return name
    return "201+ vertices"


# ---------------------------------------------------------------------------
# Helpers JSON / parsing
# ---------------------------------------------------------------------------

def _normalize_json(obj):
    """
    Nettoie récursivement les clés de dictionnaires et les chaînes.
    Utile si le JSON contient des clés comme "algorithm " ou des valeurs comme "greedy ".
    """
    if isinstance(obj, dict):
        return {str(k).strip(): _normalize_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_normalize_json(x) for x in obj]
    if isinstance(obj, str):
        return obj.strip()
    return obj


def _to_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _coerce_gap(value):
    try:
        gap = float(value)
        if gap.is_integer():
            return int(gap)
        return gap
    except (TypeError, ValueError):
        return 0


# ---------------------------------------------------------------------------
# Parsing des JSON
# ---------------------------------------------------------------------------

def scanner(directory):
    """Retourne la liste triée des chemins de fichiers .json (non récursif)."""
    json_files = []
    for f in os.listdir(directory):
        if f.endswith(".json"):
            json_files.append(os.path.join(directory, f))
    return sorted(json_files)


def analyser_json(path):
    """Extrait les informations pertinentes d'un fichier JSON."""
    with open(path, encoding="utf-8") as f:
        data = _normalize_json(json.load(f))

    if not isinstance(data, dict):
        data = {}

    instance = data.get("instance", {}) or {}
    ground_truth = data.get("ground_truth", {}) or {}
    labels = data.get("labels", {}) or {}
    results_raw = data.get("results", []) or []

    adj_matrix = instance.get("adjacency_matrix", []) or []

    n_vertices = _to_int(instance.get("n_vertices", 0), 0)
    n_edges = _to_int(instance.get("n_edges", 0), 0)

    # Si n_edges absent / à 0 mais matrice présente, on recalcule.
    if n_edges == 0 and adj_matrix:
        computed_edges = 0
        for i in range(len(adj_matrix)):
            row = adj_matrix[i] if isinstance(adj_matrix[i], list) else []
            for j in range(i + 1, len(row)):
                try:
                    if int(row[j]):
                        computed_edges += 1
                except Exception:
                    pass
        n_edges = computed_edges

    adjacency = []
    for row in adj_matrix:
        try:
            adjacency.append("".join(str(int(x)) for x in row))
        except Exception:
            adjacency.append("")

    chi = _to_int(ground_truth.get("chi", 0), 0)

    results = {}
    for r in results_raw:
        if not isinstance(r, dict):
            continue

        algo = str(r.get("algorithm", "")).strip()
        if not algo:
            continue

        n_colors = _to_int(r.get("n_colors", 0), 0)

        # Priorité : recalculer le gap depuis chi si possible.
        if chi > 0:
            gap = max(0, n_colors - chi)
        else:
            gap = _coerce_gap(r.get("gap_to_chi", 0))

        optimal = bool(r.get("optimal", False)) or (chi > 0 and n_colors == chi)

        results[algo] = {
            "n_colors": n_colors,
            "gap_to_chi": gap,
            "optimal": optimal,
            "time_ms": _to_float(r.get("time_ms", 0.0), 0.0),
            "solution": r.get("solution", []) or [],
        }

    # Calculer la densité si non présente
    max_edges = n_vertices * (n_vertices - 1) / 2 if n_vertices > 1 else 1
    density = n_edges / max_edges if max_edges > 0 else 0.0

    run_id = os.path.splitext(os.path.basename(path))[0]

    # Best algorithm / best_n_colors : utiliser les labels si présents,
    # sinon recalculer depuis les résultats.
    best_algorithm = str(labels.get("best_algorithm", "")).strip()
    best_n_colors = _to_int(labels.get("best_n_colors", 0), 0)

    if results:
        # Ignore solvers that timed out / errored (n_colors < 0) when picking the best.
        computed = {a: r for a, r in results.items() if r["n_colors"] >= 0}
        if computed:
            computed_best_algo, computed_best_res = min(
                computed.items(),
                key=lambda kv: (
                    kv[1]["n_colors"],
                    kv[1]["gap_to_chi"],
                    kv[1]["time_ms"],
                ),
            )
        else:
            computed_best_algo, computed_best_res = next(iter(results.items()))

        if not best_algorithm:
            best_algorithm = computed_best_algo

        if best_n_colors <= 0:
            best_n_colors = computed_best_res["n_colors"]

    optimal_algorithms = sorted([algo for algo, r in results.items() if r["optimal"]])
    if not optimal_algorithms:
        optimal_algorithms = sorted(
            [str(x).strip() for x in labels.get("optimal_algorithms", []) if str(x).strip()]
        )

    return {
        "run_id": run_id,
        "chi": chi,
        "n_vertices": n_vertices,
        "n_edges": n_edges,
        "density": density,
        "graph_type": instance.get("type", "") or "unknown",
        "params": instance.get("params", {}) or {},
        "adjacency": adjacency,
        "results": results,
        "best_algorithm": best_algorithm,
        "optimal_algorithms": optimal_algorithms,
        "n_optimal_algorithms": len(optimal_algorithms),
        "best_n_colors": best_n_colors,
    }


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

STYLE = """
:root{
  --bg:#0B111A; --fig:#0E1621; --panel:#16222F; --panel2:#1B2A3A;
  --frame:#2C4054; --frame2:#35506A;
  --ink:#EAF2F7; --text:#93A9B8; --muted:#5D7284;
  --teal:#2FBFAE; --teal-hi:#A8DFF0; --amber:#F5A83C;
  --ok:#6EE7A0; --bad:#FF8A7A;
  --mono:'IBM Plex Mono',ui-monospace,Menlo,Consolas,monospace;
  --disp:'Space Grotesk',-apple-system,'Segoe UI',Roboto,sans-serif;
}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:var(--disp);background:var(--bg);color:var(--text);
line-height:1.6;padding:48px 20px;min-height:100vh}
body::before{content:"";position:fixed;inset:0;z-index:0;pointer-events:none;
background-image:linear-gradient(rgba(163,214,255,.035) 1px,transparent 1px),
linear-gradient(90deg,rgba(163,214,255,.035) 1px,transparent 1px);
background-size:44px 44px}
body::after{content:"";position:fixed;inset:0;z-index:0;pointer-events:none;
background:radial-gradient(720px 420px at 12% -5%,rgba(47,191,174,.09),transparent 60%),
radial-gradient(640px 420px at 92% 105%,rgba(245,168,60,.06),transparent 60%)}
.page{position:relative;z-index:1;max-width:1040px;margin:0 auto;background:var(--fig);
border:1px solid var(--frame);border-radius:14px;overflow:hidden;
box-shadow:0 24px 60px rgba(0,0,0,.5)}
header{background:linear-gradient(135deg,#0E1621 0%,#131F2E 55%,#16222F 100%);
border-bottom:1px solid var(--frame);padding:32px 40px;
display:flex;justify-content:space-between;align-items:center;gap:24px;flex-wrap:wrap}
header h1{font-size:1.7rem;font-weight:700;color:var(--ink);letter-spacing:-.02em}
header .meta{font-family:var(--mono);font-size:.74rem;color:var(--muted);margin-top:8px}
header .meta b{color:var(--teal);font-weight:500}
.chi-badge{background:var(--panel);border:1px solid var(--frame);border-radius:12px;
padding:12px 28px;text-align:center;flex-shrink:0;cursor:help}
.chi-badge .k{display:block;font-family:var(--mono);font-size:.6rem;letter-spacing:.18em;
text-transform:uppercase;color:var(--muted)}
.chi-badge .v{font-size:2.6rem;font-weight:700;color:var(--teal-hi);line-height:1.15}
.banner{display:flex;flex-wrap:wrap;border-bottom:1px solid var(--frame)}
.bitem{flex:1 1 180px;padding:16px 24px;border-right:1px solid var(--frame)}
.bitem:last-child{border-right:none}
.bk{display:block;font-family:var(--mono);font-size:.6rem;letter-spacing:.16em;
text-transform:uppercase;color:var(--muted)}
.bv{font-size:1.25rem;font-weight:700;color:var(--ink);margin-top:2px}
.bv .star{color:var(--amber)}
section{padding:28px 40px}
h2{font-family:var(--mono);font-size:.72rem;letter-spacing:.2em;text-transform:uppercase;
color:var(--teal);margin-bottom:18px;display:flex;align-items:center;gap:10px}
h2::before{content:"";width:8px;height:8px;background:var(--teal);flex-shrink:0}
h2 .hint{margin-left:auto;font-size:.62rem;letter-spacing:.08em;color:var(--muted);
text-transform:none;font-weight:400}
table{width:100%;border-collapse:collapse;font-size:.9rem}
th{font-family:var(--mono);font-size:.6rem;letter-spacing:.14em;text-transform:uppercase;
color:var(--muted);text-align:left;padding:11px 16px;background:var(--panel);
border-bottom:1px solid var(--frame)}
td{padding:12px 16px;border-bottom:1px solid rgba(44,64,84,.5)}
tbody tr{transition:background .2s;cursor:pointer}
tbody tr:hover{background:rgba(47,191,174,.05)}
tbody tr.active{background:rgba(47,191,174,.1)}
td.num{font-family:var(--mono)}
.algo-name{color:var(--ink);font-weight:600}
.arrow{color:var(--teal);font-size:.7rem;margin-left:8px;opacity:0;transition:opacity .2s}
tbody tr:hover .arrow,tbody tr.active .arrow{opacity:1}
.pct{position:relative;white-space:nowrap}
.bar{position:absolute;left:0;bottom:0;height:2px;background:var(--teal);
opacity:.55;transition:width .5s ease}
.density-bar{display:flex;align-items:center;gap:12px}
.density-bar .track{flex:1;height:10px;background:var(--panel2);border-radius:5px;
overflow:hidden;border:1px solid var(--frame)}
.density-bar .fill{height:100%;background:linear-gradient(90deg,var(--teal),var(--teal-hi));
border-radius:5px;transition:width .6s ease}
.density-bar .val{font-family:var(--mono);font-size:.78rem;color:var(--ink);min-width:36px;text-align:right}
.cat-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:16px}
.cat-card{background:var(--panel);border:1px solid var(--frame);border-radius:10px;
padding:18px 20px;transition:border-color .2s}
.cat-card:hover{border-color:var(--frame2)}
.cat-card .clabel{font-family:var(--mono);font-size:.62rem;letter-spacing:.12em;
text-transform:uppercase;color:var(--muted)}
.cat-card .cval{font-size:1.8rem;font-weight:700;color:var(--ink);margin-top:4px}
.cat-card .csub{font-family:var(--mono);font-size:.66rem;color:var(--teal);margin-top:4px}
.explain{background:var(--panel);border:1px solid var(--frame);border-radius:10px;
padding:18px 22px;margin-bottom:22px;font-size:.85rem;line-height:1.7}
.explain b{color:var(--teal-hi);font-weight:600}
.explain .ex-title{font-family:var(--mono);font-size:.62rem;letter-spacing:.16em;
text-transform:uppercase;color:var(--teal);margin-bottom:10px;
display:flex;align-items:center;gap:8px}
.explain .ex-title::before{content:"💡";font-size:.9rem}
.explain ul{margin:8px 0 0 18px}
.explain li{margin-bottom:6px}
.explain .ex-note{color:var(--amber);font-weight:500}
.union-bar{display:flex;align-items:center;gap:12px;margin-bottom:18px;flex-wrap:wrap}
.union-btn{background:var(--teal);color:#08141A;border:none;border-radius:8px;
font-family:var(--mono);font-size:.68rem;font-weight:700;letter-spacing:.1em;
text-transform:uppercase;padding:10px 18px;cursor:pointer;
transition:background .2s,transform .2s}
.union-btn:hover{background:var(--teal-hi);transform:translateY(-1px)}
.union-btn.active{background:var(--amber)}
.union-status{font-family:var(--mono);font-size:.7rem;color:var(--muted)}
.union-panel{display:none;background:var(--panel);border:1px solid var(--frame);
border-radius:10px;padding:18px 22px;margin-bottom:22px}
.union-panel.show{display:block;animation:rise .3s cubic-bezier(.2,.7,.2,1)}
.union-panel h3{font-family:var(--mono);font-size:.62rem;letter-spacing:.16em;
text-transform:uppercase;color:var(--teal);margin-bottom:12px}
.union-algos{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:14px}
.union-algo{display:flex;align-items:center;gap:8px;background:var(--panel2);
border:1px solid var(--frame2);border-radius:8px;padding:6px 12px;
cursor:pointer;transition:border-color .2s,background .2s;user-select:none}
.union-algo:hover{border-color:var(--teal)}
.union-algo input{accent-color:var(--teal);cursor:pointer}
.union-algo span{font-family:var(--mono);font-size:.72rem;color:var(--ink)}
.union-algo.selected{background:#203041;border-color:var(--teal)}
.union-actions{display:flex;gap:10px;flex-wrap:wrap}
.union-source{margin-bottom:14px}
.union-source label,.union-dest label{display:block;font-family:var(--mono);font-size:.62rem;letter-spacing:.12em;
text-transform:uppercase;color:var(--muted);margin-bottom:6px}
.source-dir-input,.dest-dir-input{width:100%;background:var(--panel2);border:1px solid var(--frame2);
border-radius:8px;color:var(--ink);font-family:var(--mono);
font-size:.72rem;padding:8px 12px;box-sizing:border-box}
.source-dir-input:focus,.dest-dir-input:focus{border-color:var(--teal);outline:none}
.union-source .hint,.union-dest .hint{font-size:.6rem;color:var(--muted);margin-top:4px;font-style:italic}
.union-dest{margin-bottom:14px}
.union-action{background:var(--panel2);border:1px solid var(--frame2);border-radius:8px;
color:var(--text);font-family:var(--mono);font-size:.68rem;padding:8px 14px;
cursor:pointer;transition:border-color .2s,color .2s}
.union-action:hover{border-color:var(--teal);color:var(--teal)}
.union-action.primary{background:var(--teal);color:#08141A;border-color:var(--teal);font-weight:700}
.union-action.primary:hover{background:var(--teal-hi)}
.union-result{margin-top:16px;border-top:1px solid var(--frame);padding-top:14px}
.union-result .dk{margin-top:0}
.union-result .chips{margin-bottom:10px}
.union-empty{font-family:var(--mono);font-size:.72rem;color:var(--muted);font-style:italic}
.union-count{font-family:var(--mono);font-size:.7rem;color:var(--teal-hi);margin-left:6px}
.union-density{margin-top:16px;border-top:1px solid var(--frame);padding-top:14px}
.union-density table{width:100%;border-collapse:collapse;font-size:.8rem;margin-top:8px}
.union-density th{font-family:var(--mono);font-size:.56rem;letter-spacing:.12em;
text-transform:uppercase;color:var(--muted);text-align:left;
padding:8px 10px;background:var(--panel2);border-bottom:1px solid var(--frame)}
.union-density td{padding:8px 10px;border-bottom:1px solid rgba(44,64,84,.5)}
.union-density .num{font-family:var(--mono)}
.union-density .pct{position:relative;white-space:nowrap}
.union-density .bar{position:absolute;left:0;bottom:0;height:2px;background:var(--teal);
opacity:.55}
.union-density .ok{color:var(--ok);font-weight:600}
.union-density .ko{color:var(--bad);font-weight:600}
.detail{border-top:1px solid var(--frame);background:var(--panel)}
.detail-body{min-height:60px}
.dk{font-family:var(--mono);font-size:.6rem;letter-spacing:.16em;
text-transform:uppercase;color:var(--muted);margin:18px 0 8px}
.dk:first-child{margin-top:0}
.dv{font-size:1.15rem;font-weight:700;color:var(--ink);margin-bottom:10px}
.dv span{color:var(--teal);font-weight:600;font-size:.85rem}
.chips{display:flex;flex-wrap:wrap;gap:8px}
.chip{font-family:var(--mono);font-size:.72rem;color:var(--teal-hi);
background:var(--panel2);border:1px solid var(--frame2);border-radius:8px;
padding:4px 12px;text-decoration:none;transition:border-color .2s,background .2s;
cursor:pointer}
.chip:hover{border-color:var(--teal);background:#203041}
.chip.active{border-color:var(--teal);background:#203041}
.none{font-family:var(--mono);font-size:.72rem;color:var(--muted);font-style:italic}
.modal-overlay{position:fixed;inset:0;z-index:100;background:rgba(5,10,18,.82);
display:none;align-items:flex-start;justify-content:center;
padding:40px 20px;overflow-y:auto;backdrop-filter:blur(4px)}
.modal-overlay.show{display:flex}
.modal{background:var(--fig);border:1px solid var(--frame);border-radius:14px;
max-width:1200px;width:100%;box-shadow:0 24px 60px rgba(0,0,0,.6);
animation:rise .35s cubic-bezier(.2,.7,.2,1)}
@keyframes rise{from{opacity:0;transform:translateY(20px)}to{opacity:1;transform:translateY(0)}}
.modal-header{background:linear-gradient(135deg,#0E1621 0%,#131F2E 55%,#16222F 100%);
border-bottom:1px solid var(--frame);padding:24px 32px;
display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap}
.modal-header h3{font-size:1.3rem;font-weight:700;color:var(--ink)}
.modal-header .meta{font-family:var(--mono);font-size:.7rem;color:var(--muted);margin-top:4px}
.modal-header .meta b{color:var(--teal);font-weight:500}
.modal-close{background:var(--panel);border:1px solid var(--frame);border-radius:8px;
color:var(--text);font-size:1.1rem;cursor:pointer;padding:6px 14px;
transition:border-color .2s,color .2s}
.modal-close:hover{border-color:var(--teal);color:var(--teal)}
.modal-body{padding:24px 32px}
.modal-table{width:100%;border-collapse:collapse;font-size:.85rem;margin-bottom:24px}
.modal-table th{font-family:var(--mono);font-size:.58rem;letter-spacing:.14em;
text-transform:uppercase;color:var(--muted);text-align:left;
padding:8px 12px;background:var(--panel);border-bottom:1px solid var(--frame)}
.modal-table td{padding:8px 12px;border-bottom:1px solid rgba(44,64,84,.5)}
.modal-table .algo-name{color:var(--ink);font-weight:600}
.modal-table .ok{color:var(--ok);font-weight:600;font-family:var(--mono);font-size:.76rem}
.modal-table .ko{color:var(--bad);font-weight:600;font-family:var(--mono);font-size:.76rem}
.modal-table .star{color:var(--amber)}
.modal-table tr.best td{background:rgba(47,191,174,.07)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(360px,1fr));gap:20px}
.card{position:relative;background:var(--panel);border:1px solid var(--frame);
border-radius:12px;padding:14px;
transition:transform .25s,box-shadow .25s,border-color .25s;
animation:rise .55s cubic-bezier(.2,.7,.2,1) backwards;
animation-delay:calc(var(--i,0)*60ms)}
.card:hover{transform:translateY(-4px);box-shadow:0 12px 28px rgba(0,0,0,.45);
border-color:var(--frame2)}
.card.best{border-color:var(--teal)}
.card.best:hover{box-shadow:0 0 0 1px var(--teal),0 12px 28px rgba(0,0,0,.45)}
figcaption{display:flex;justify-content:space-between;align-items:center;gap:8px;
font-family:var(--mono);font-size:.68rem;color:var(--muted);margin-bottom:10px}
figcaption b{color:var(--ink);font-weight:600}
.badge{background:var(--teal);color:#08141A;font-size:.54rem;font-weight:700;
padding:2px 8px;border-radius:10px;text-transform:uppercase;letter-spacing:.08em}
.svg-wrap{position:relative}
.panel-line{font-family:var(--mono);font-size:.64rem;color:var(--muted);margin-top:10px;
padding-top:8px;border-top:1px solid rgba(44,64,84,.5)}
.panel-line b{color:var(--teal-hi);font-weight:600}
.gtip{position:absolute;z-index:10;pointer-events:none;background:var(--panel2);
border:1px solid var(--frame2);border-radius:8px;padding:8px 12px;
font-family:var(--mono);font-size:.66rem;line-height:1.5;color:var(--text);
box-shadow:0 8px 20px rgba(0,0,0,.55);white-space:nowrap;
opacity:0;transform:translateY(4px);transition:opacity .18s,transform .18s}
.gtip.show{opacity:1;transform:translateY(0)}
.gtip b{color:var(--teal-hi)}
.graph-svg{width:100%;height:auto;display:block}
.graph-svg .edge{stroke:var(--frame);stroke-width:2.2;fill:none;
transition:stroke .25s,opacity .25s,stroke-width .25s}
.graph-svg .edge.lit{stroke:var(--teal-hi);stroke-width:4}
.graph-svg .edge.dim{opacity:.1}
.graph-svg .glow{opacity:.14;transition:opacity .25s}
.graph-svg .glow.lit{opacity:.32}
.graph-svg .glow.dim{opacity:.03}
.graph-svg .node{cursor:pointer;transition:opacity .25s,stroke-width .25s,stroke .25s}
.graph-svg .node.lit{stroke:#EAF6FF;stroke-width:4}
.graph-svg .node.dim{opacity:.15}
.graph-svg .nlabel{pointer-events:none;transition:opacity .25s}
.graph-svg .nlabel.dim{opacity:.15}
footer{padding:18px 40px;border-top:1px solid var(--frame);font-family:var(--mono);
font-size:.66rem;letter-spacing:.06em;color:var(--muted)}
@media (max-width:640px){header{padding:24px}section{padding:24px}
header h1{font-size:1.35rem}.chi-badge .v{font-size:2rem}
.grid{grid-template-columns:1fr}}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
"""


# ---------------------------------------------------------------------------
# JavaScript
# ---------------------------------------------------------------------------

SCRIPT = r"""
(function () {
  var STATS = __STATS__;
  var GRAPHS = __GRAPHS__;
  var ALGOS = __ALGOS__;
  var TOTAL = __TOTAL__;
  var SOURCE_DIR = __SOURCE_DIR__;

  var currentOptSet = {};
  var currentNonSet = {};

  var PALETTE = [
    "#F5A83C", "#2FBFAE", "#EE7FA9", "#7B9CF5",
    "#A3D65C", "#F0795B", "#5AC8E8", "#C88BE0",
    "#E8C547", "#63D6B1", "#D98AD9", "#8FB8FF"
  ];

  function palette(nb) {
    if (nb <= PALETTE.length) return PALETTE.slice(0, nb);
    var cols = [];
    for (var i = 0; i < nb; i++) {
      var h = i / nb;
      var s = 0.62, v = 0.92;
      var hi = Math.floor(h * 6), f = h * 6 - hi, p = v * (1 - s),
          q = v * (1 - f * s), t = v * (1 - (1 - f) * s);
      var r, g, b;
      switch (hi % 6) {
        case 0: r = v; g = t; b = p; break;
        case 1: r = q; g = v; b = p; break;
        case 2: r = p; g = v; b = t; break;
        case 3: r = p; g = q; b = v; break;
        case 4: r = t; g = p; b = v; break;
        default: r = v; g = p; b = q;
      }
      cols.push('#' + ('0' + Math.round(r * 255).toString(16)).slice(-2)
                + ('0' + Math.round(g * 255).toString(16)).slice(-2)
                + ('0' + Math.round(b * 255).toString(16)).slice(-2));
    }
    return cols;
  }

  function shade(hex, factor) {
    var r = parseInt(hex.substr(1, 2), 16),
        g = parseInt(hex.substr(3, 2), 16),
        b = parseInt(hex.substr(5, 2), 16);
    factor = factor || 0.66;
    return '#' + ('0' + Math.round(r * factor).toString(16)).slice(-2)
                 + ('0' + Math.round(g * factor).toString(16)).slice(-2)
                 + ('0' + Math.round(b * factor).toString(16)).slice(-2);
  }

  function labelColor(hex) {
    var r = parseInt(hex.substr(1, 2), 16) / 255,
        g = parseInt(hex.substr(3, 2), 16) / 255,
        b = parseInt(hex.substr(5, 2), 16) / 255;
    var lum = 0.2126 * r + 0.7152 * g + 0.0722 * b;
    return lum > 0.6 ? '#0F1822' : '#F4F8FB';
  }

  function safeGap(g, r) {
    if (!g || !r) return 0;
    var chi = Number(g.chi || 0);
    var n = Number(r.n_colors || 0);
    if (chi > 0 && isFinite(n)) {
      return Math.max(0, n - chi);
    }
    var gap = Number(r.gap_to_chi || 0);
    return isFinite(gap) ? gap : 0;
  }

  function formatGap(gap) {
    var g = Number(gap || 0);
    if (!isFinite(g)) return '0';
    return Math.floor(g) === g ? String(g) : g.toFixed(2);
  }

  function drawGraph(adj, colors, taille) {
    taille = taille || 400;
    colors = colors || [];
    var n = adj.length;
    if (n === 0) return '';

    var cx = taille / 2, cy = taille / 2;
    var rayon = taille / 2 - 44;
    var pos = [];
    for (var i = 0; i < n; i++) {
      var angle = 2 * Math.PI * i / n - Math.PI / 2;
      pos.push([cx + rayon * Math.cos(angle), cy + rayon * Math.sin(angle)]);
    }

    var used = [];
    for (var i = 0; i < n; i++) {
      var col = colors[i] === undefined ? 0 : colors[i];
      if (used.indexOf(col) === -1) used.push(col);
    }
    used.sort(function (a, b) { return a - b; });

    var pal = palette(used.length);
    var idx = {};
    for (var i = 0; i < used.length; i++) idx[used[i]] = i;

    var deg = [], voisins = [];
    for (var i = 0; i < n; i++) {
      var d = 0, v = [];
      for (var j = 0; j < n; j++) {
        if (parseInt(adj[i][j], 10) === 1) {
          d++;
          v.push(j);
        }
      }
      deg.push(d);
      voisins.push(v);
    }

    var nodeR = Math.max(10, Math.min(20, 150 / n));
    var glowR = nodeR * 1.7;
    var parts = ['<svg class="graph-svg" viewBox="0 0 ' + taille + ' ' + taille +
                 '" xmlns="http://www.w3.org/2000/svg" role="img">'];

    for (var i = 0; i < n; i++) {
      for (var j = i + 1; j < n; j++) {
        if (parseInt(adj[i][j], 10) === 1) {
          var x1 = pos[i][0], y1 = pos[i][1], x2 = pos[j][0], y2 = pos[j][1];
          var mx = (x1 + x2) / 2, my = (y1 + y2) / 2;
          var dx = x2 - x1, dy = y2 - y1;
          var dist = Math.sqrt(dx * dx + dy * dy) || 1.0;
          var off = 0.12 * dist;
          var qx = mx + (-dy / dist) * off, qy = my + (dx / dist) * off;
          parts.push('<path class="edge" data-a="' + i + '" data-b="' + j +
                     '" d="M ' + x1.toFixed(1) + ' ' + y1.toFixed(1) + ' Q ' +
                     qx.toFixed(1) + ' ' + qy.toFixed(1) + ' ' + x2.toFixed(1) +
                     ' ' + y2.toFixed(1) + '"/>');
        }
      }
    }

    for (var i = 0; i < n; i++) {
      var col = colors[i] === undefined ? 0 : colors[i];
      var c = pal[idx[col]];
      parts.push('<circle class="glow" data-v="' + i + '" cx="' + pos[i][0].toFixed(1) +
                 '" cy="' + pos[i][1].toFixed(1) + '" r="' + glowR.toFixed(1) +
                 '" fill="' + c + '"/>');
    }

    for (var i = 0; i < n; i++) {
      var col = colors[i] === undefined ? 0 : colors[i];
      var c = pal[idx[col]];
      var neighStr = voisins[i].join(',');
      parts.push('<circle class="node" data-v="' + i + '" data-deg="' + deg[i] +
                 '" data-neighbors="' + neighStr + '" cx="' + pos[i][0].toFixed(1) +
                 '" cy="' + pos[i][1].toFixed(1) + '" r="' + nodeR.toFixed(1) +
                 '" fill="' + c + '" stroke="' + shade(c) + '" stroke-width="2.5"/>');
      parts.push('<text class="nlabel" data-v="' + i + '" x="' + pos[i][0].toFixed(1) +
                 '" y="' + pos[i][1].toFixed(1) + '" dy="5" text-anchor="middle" ' +
                 'font-size="13" font-weight="700" fill="' + labelColor(c) + '">' + i + '</text>');
    }

    parts.push('</svg>');
    return parts.join('');
  }

  function attachHover(svg, card) {
    var tip = card.querySelector('.gtip');
    if (!tip) return;

    var nodes = svg.querySelectorAll('.node');
    var edges = svg.querySelectorAll('.edge');
    var glows = svg.querySelectorAll('.glow');
    var labs = svg.querySelectorAll('.nlabel');

    function reset() {
      nodes.forEach(function (x) { x.classList.remove('lit', 'dim'); });
      edges.forEach(function (x) { x.classList.remove('lit', 'dim'); });
      glows.forEach(function (x) { x.classList.remove('lit', 'dim'); });
      labs.forEach(function (x) { x.classList.remove('dim'); });
      tip.classList.remove('show');
    }

    nodes.forEach(function (node) {
      node.addEventListener('mouseenter', function () {
        var v = parseInt(node.dataset.v, 10);
        var neigh = new Set(
          node.dataset.neighbors.split(',').filter(function (s) { return s !== ''; })
            .map(function (s) { return parseInt(s, 10); })
        );
        neigh.add(v);

        nodes.forEach(function (x) {
          var i = parseInt(x.dataset.v, 10);
          x.classList.toggle('lit', i === v);
          x.classList.toggle('dim', !neigh.has(i));
        });

        glows.forEach(function (x) {
          var i = parseInt(x.dataset.v, 10);
          x.classList.toggle('lit', i === v);
          x.classList.toggle('dim', !neigh.has(i));
        });

        labs.forEach(function (x) {
          var i = parseInt(x.dataset.v, 10);
          x.classList.toggle('dim', !neigh.has(i));
        });

        edges.forEach(function (x) {
          var a = parseInt(x.dataset.a, 10), b = parseInt(x.dataset.b, 10);
          var on = (a === v || b === v);
          x.classList.toggle('lit', on);
          x.classList.toggle('dim', !on);
        });

        var nb = node.dataset.neighbors
          ? node.dataset.neighbors.replace(/,/g, ', ')
          : '—';

        tip.innerHTML = '<b>vertex ' + v + '</b> · degree ' + node.dataset.deg +
                        '<br>neighbors: ' + nb;
        tip.classList.add('show');
      });

      node.addEventListener('mousemove', function (e) {
        var r = card.getBoundingClientRect();
        tip.style.left = (e.clientX - r.left + 14) + 'px';
        tip.style.top = (e.clientY - r.top + 14) + 'px';
      });

      node.addEventListener('mouseleave', reset);
    });
  }

  // --- union builder ---
  var unionBtn = document.getElementById('union-btn');
  var unionPanel = document.getElementById('union-panel');
  var unionAlgos = document.getElementById('union-algos');
  var unionResult = document.getElementById('union-result');
  var unionStatus = document.getElementById('union-status');
  var sourceDirInput = document.getElementById('source-dir-input');

  if (sourceDirInput) sourceDirInput.value = SOURCE_DIR;

  var unionChecks = {};

  ALGOS.forEach(function (pair) {
    var disp = pair[0], json = pair[1];

    var label = document.createElement('label');
    label.className = 'union-algo';

    var cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.value = json;
    cb.dataset.disp = disp;

    var span = document.createElement('span');
    span.textContent = disp;

    label.appendChild(cb);
    label.appendChild(span);

    label.addEventListener('click', function (e) {
      if (e.target !== cb) cb.checked = !cb.checked;
      label.classList.toggle('selected', cb.checked);
    });

    unionAlgos.appendChild(label);
    unionChecks[json] = cb;
  });

  function selectedUnionAlgos() {
    return Object.keys(unionChecks).filter(function (k) { return unionChecks[k].checked; });
  }

  var DENSITY_CATS = [
    ['Very dense', 0.75, 1.01],
    ['Dense', 0.50, 0.75],
    ['Moderately dense', 0.25, 0.50],
    ['Sparse', 0.10, 0.25],
    ['Very sparse', 0.00, 0.10]
  ];

  function densityCat(d) {
    for (var i = 0; i < DENSITY_CATS.length; i++) {
      if (d >= DENSITY_CATS[i][1] && d < DENSITY_CATS[i][2]) return DENSITY_CATS[i][0];
    }
    return 'Very sparse';
  }

  function getOptimalIds() {
    return Object.keys(currentOptSet).sort();
  }

  function getNonOptimalIds() {
    return Object.keys(currentNonSet).sort();
  }

  function getSourceDir() {
    var input = document.getElementById('source-dir-input');
    return input ? input.value : SOURCE_DIR;
  }

  function getDestDir() {
    var input = document.getElementById('dest-dir-input');
    return input ? input.value.trim() : '';
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function bashSingleQuote(s) {
    var bs = String.fromCharCode(92);
    return "'" + String(s).replace(/'/g, function () {
      return "'" + bs + "'" + "'";
    }) + "'";
  }

  function bestSelectedResult(id, selected) {
    var g = GRAPHS[id] || {};
    var results = g.results || {};
    var best = null;

    selected.forEach(function (jsonName) {
      var r = results[jsonName];
      if (!r || typeof r.n_colors === 'undefined') return;

      var colors = Number(r.n_colors || 0);
      var gap = safeGap(g, r);
      var time = Number(r.time_ms || 0);

      if (!best ||
          colors < best.colors ||
          (colors === best.colors && gap < best.gap) ||
          (colors === best.colors && gap === best.gap && time < best.time)) {
        best = { colors: colors, gap: gap, time: time, algo: jsonName };
      }
    });

    // Fallback only if no selected result exists at all.
    if (!best && g.best_algorithm && results[g.best_algorithm]) {
      var r2 = results[g.best_algorithm];
      best = {
        colors: Number(r2.n_colors || 0),
        gap: safeGap(g, r2),
        time: Number(r2.time_ms || 0),
        algo: g.best_algorithm
      };
    }

    if (!best) {
      best = { colors: Number(g.best_n_colors || 0), gap: 0, time: 0, algo: '' };
    }

    return best;
  }

  function renderUnion() {
    var sel = selectedUnionAlgos();

    if (!sel.length) {
      unionResult.innerHTML = '<span class="union-empty">Select at least one algorithm.</span>';
      currentOptSet = {};
      currentNonSet = {};
      return;
    }

    var optSet = {};
    var nonSet = {};

    Object.keys(GRAPHS).forEach(function (id) {
      var g = GRAPHS[id] || {};
      var results = g.results || {};

      var anySelected = false;
      var anyOptimal = false;
      var allNonOptimal = true;

      sel.forEach(function (jsonName) {
        var r = results[jsonName];

        // To be "all non-optimal", every selected algorithm must be present and non-optimal.
        if (!r) {
          allNonOptimal = false;
          return;
        }

        anySelected = true;

        var chi = Number(g.chi || 0);
        var n = Number(r.n_colors || 0);
        var isOpt = Boolean(r.optimal) || (chi > 0 && n === chi);

        if (isOpt) {
          anyOptimal = true;
          allNonOptimal = false;
        }
      });

      if (anyOptimal) optSet[id] = true;
      if (anySelected && allNonOptimal) nonSet[id] = true;
    });

    currentOptSet = optSet;
    currentNonSet = nonSet;

    var optIds = Object.keys(optSet).sort();
    var nonIds = Object.keys(nonSet).sort();

    var optEntries = optIds.map(function (id) {
      var b = bestSelectedResult(id, sel);
      return { run_id: id, label: id, colors: b.colors, gap: b.gap };
    });

    var nonEntries = nonIds.map(function (id) {
      var b = bestSelectedResult(id, sel);
      return { run_id: id, label: id, colors: b.colors, gap: b.gap };
    });

    var pctOpt = TOTAL ? (optIds.length / TOTAL * 100).toFixed(1) : '0.0';
    var pctNon = TOTAL ? (nonIds.length / TOTAL * 100).toFixed(1) : '0.0';

    var catTotal = {};
    var catOpt = {};

    DENSITY_CATS.forEach(function (c) {
      catTotal[c[0]] = 0;
      catOpt[c[0]] = 0;
    });

    Object.keys(GRAPHS).forEach(function (runId) {
      var g = GRAPHS[runId];
      var cat = densityCat(Number(g.density || 0));
      catTotal[cat] = (catTotal[cat] || 0) + 1;
      if (optSet[runId]) catOpt[cat] = (catOpt[cat] || 0) + 1;
    });

    var densityRows = '';

    DENSITY_CATS.forEach(function (c) {
      var name = c[0];
      var tot = catTotal[name] || 0;
      var opt = catOpt[name] || 0;
      if (tot === 0) return;

      var pct = (opt / tot * 100).toFixed(1);
      var cls = (opt === tot) ? 'ok' : (opt === 0 ? 'ko' : '');

      densityRows += '<tr>' +
        '<td class="algo-name">' + name + '</td>' +
        '<td class="num">' + tot + '</td>' +
        '<td class="num">' + opt + '</td>' +
        '<td class="num pct"><span class="bar" style="width:' + pct + '%"></span>' + pct + ' %</td>' +
        '<td class="num ' + cls + '">' + (opt === tot ? '✓ all' : (opt === 0 ? '✗ none' : 'partial')) + '</td>' +
        '</tr>';
    });

    var densityHtml = '<div class="union-density">' +
      '<div class="dk">Optimality per density category</div>' +
      '<table><thead><tr><th>Density</th><th>Graphs</th><th>Optimal</th><th>% optimal</th><th>Status</th></tr></thead>' +
      '<tbody>' + densityRows + '</tbody></table></div>';

    var noteHtml = '<div class="hint" style="font-size:.66rem;color:var(--muted);margin:4px 0 12px 0;font-style:italic;">' +
      'Format: <b>[ID]</b> · <b>[Colors]</b>c +<b>[Gap]</b> (best result among selected algorithms)' +
      '</div>';

    unionResult.innerHTML =
      '<div class="dk">Union — optimal  ·  ' + optIds.length + ' / ' + TOTAL +
      '  (' + pctOpt + ' %)<span class="union-count">' + sel.length + ' algo(s)</span></div>' +
      noteHtml +
      '<div class="chips">' + chips(optEntries, 'optimal') + '</div>' +
      '<div class="dk">Union — non-optimal  ·  ' + nonIds.length + ' / ' + TOTAL +
      '  (' + pctNon + ' %)</div>' +
      '<div class="chips">' + chips(nonEntries, 'non_optimal') + '</div>' +
      densityHtml;

    unionResult.querySelectorAll('.chip').forEach(function (chip) {
      chip.addEventListener('click', function () { showGraph(chip.dataset.run); });
    });
  }

  unionBtn.addEventListener('click', function () {
    var show = !unionPanel.classList.contains('show');
    unionPanel.classList.toggle('show', show);
    unionBtn.classList.toggle('active', show);

    if (show) {
      unionStatus.textContent = 'Select algorithms — the union of their optimal files will be computed';
    } else {
      unionStatus.textContent = 'Select algorithms to compute the union of their optimal files';
    }
  });

  document.getElementById('union-compute').addEventListener('click', renderUnion);

  document.getElementById('union-clear').addEventListener('click', function () {
    Object.keys(unionChecks).forEach(function (k) {
      unionChecks[k].checked = false;
      unionChecks[k].closest('.union-algo').classList.remove('selected');
    });
    unionResult.innerHTML = '';
    currentOptSet = {};
    currentNonSet = {};
  });

  document.getElementById('union-close').addEventListener('click', function () {
    unionPanel.classList.remove('show');
    unionBtn.classList.remove('active');
    unionStatus.textContent = 'Select algorithms to compute the union of their optimal files';
  });

  document.getElementById('export-ids-btn').addEventListener('click', function () {
    var ids = getOptimalIds();
    if (ids.length === 0) {
      alert('No optimal file selected.');
      return;
    }

    navigator.clipboard.writeText(ids.join('\n')).then(function () {
      alert(ids.length + ' IDs copied to the clipboard.');
    }).catch(function () {
      prompt('Copy the IDs below:', ids.join('\n'));
    });
  });

  document.getElementById('export-script-btn').addEventListener('click', function () {
    var ids = getOptimalIds();
    if (ids.length === 0) {
      alert('No optimal file selected.');
      return;
    }

    var dest = getDestDir();

    var script = '#!/bin/bash\n';
    script += '# Copy the optimal JSON files for the selected union\n';
    script += 'SOURCE_DIR=' + bashSingleQuote(getSourceDir()) + '\n';

    if (dest) {
      script += 'DEST_DIR=' + bashSingleQuote(dest) + '\n';
      script += 'mkdir -p "$DEST_DIR"\n';
    }

    script += 'ids=(' + ids.map(bashSingleQuote).join(' ') + ')\n';
    script += 'for id in "${ids[@]}"; do\n';
    script += '    cp "$SOURCE_DIR/$id.json" ' + (dest ? '"$DEST_DIR/"' : '.') + '\n';
    script += 'done\n';
    script += 'echo "Copy finished."\n';

    var blob = new Blob([script], { type: 'text/plain' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = 'copy_optimal_union.sh';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  });

  document.getElementById('export-ids-non-btn').addEventListener('click', function () {
    var ids = getNonOptimalIds();
    if (ids.length === 0) {
      alert('No non-optimal file selected.');
      return;
    }

    navigator.clipboard.writeText(ids.join('\n')).then(function () {
      alert(ids.length + ' IDs copied to the clipboard.');
    }).catch(function () {
      prompt('Copy the IDs below:', ids.join('\n'));
    });
  });

  document.getElementById('export-script-non-btn').addEventListener('click', function () {
    var ids = getNonOptimalIds();
    if (ids.length === 0) {
      alert('No non-optimal file selected.');
      return;
    }

    var dest = getDestDir();

    var script = '#!/bin/bash\n';
    script += '# Copy the non-optimal JSON files for the selected union\n';
    script += 'SOURCE_DIR=' + bashSingleQuote(getSourceDir()) + '\n';

    if (dest) {
      script += 'DEST_DIR=' + bashSingleQuote(dest) + '\n';
      script += 'mkdir -p "$DEST_DIR"\n';
    }

    script += 'ids=(' + ids.map(bashSingleQuote).join(' ') + ')\n';
    script += 'for id in "${ids[@]}"; do\n';
    script += '    cp "$SOURCE_DIR/$id.json" ' + (dest ? '"$DEST_DIR/"' : '.') + '\n';
    script += 'done\n';
    script += 'echo "Copy finished."\n';

    var blob = new Blob([script], { type: 'text/plain' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = 'copy_non_optimal_union.sh';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  });

  document.getElementById('export-script-bat-btn').addEventListener('click', function () {
    var ids = getOptimalIds();
    if (ids.length === 0) {
      alert('No optimal file selected.');
      return;
    }

    var bs = String.fromCharCode(92);
    var winPath = getSourceDir().split('/').join(bs);
    var dest = getDestDir();
    var winDest = dest ? dest.split('/').join(bs) : '';

    var script = '@echo off\r\n';
    script += 'REM Copy the optimal JSON files for the selected union\r\n';
    script += 'set "SOURCE_DIR=' + winPath + '"\r\n';

    if (winDest) {
      script += 'set "DEST_DIR=' + winDest + '"\r\n';
      script += 'if not exist "%DEST_DIR%" mkdir "%DEST_DIR%"\r\n';
    }

    ids.forEach(function (id) {
      var safeId = String(id).replace(/"/g, '""');
      var target = winDest ? '"%DEST_DIR%' + bs + '"' : '.';
      script += 'copy "%SOURCE_DIR%' + bs + safeId + '.json" ' + target + '\r\n';
    });

    script += 'echo Copy finished.\r\n';

    var blob = new Blob([script], { type: 'text/plain' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = 'copy_optimal_union.bat';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  });

  document.getElementById('export-script-bat-non-btn').addEventListener('click', function () {
    var ids = getNonOptimalIds();
    if (ids.length === 0) {
      alert('No non-optimal file selected.');
      return;
    }

    var bs = String.fromCharCode(92);
    var winPath = getSourceDir().split('/').join(bs);
    var dest = getDestDir();
    var winDest = dest ? dest.split('/').join(bs) : '';

    var script = '@echo off\r\n';
    script += 'REM Copy the non-optimal JSON files for the selected union\r\n';
    script += 'set "SOURCE_DIR=' + winPath + '"\r\n';

    if (winDest) {
      script += 'set "DEST_DIR=' + winDest + '"\r\n';
      script += 'if not exist "%DEST_DIR%" mkdir "%DEST_DIR%"\r\n';
    }

    ids.forEach(function (id) {
      var safeId = String(id).replace(/"/g, '""');
      var target = winDest ? '"%DEST_DIR%' + bs + '"' : '.';
      script += 'copy "%SOURCE_DIR%' + bs + safeId + '.json" ' + target + '\r\n';
    });

    script += 'echo Copy finished.\r\n';

    var blob = new Blob([script], { type: 'text/plain' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = 'copy_non_optimal_union.bat';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  });

  // --- algo table row clicks ---
  var rows = document.querySelectorAll('#algo-table tbody tr');
  var title = document.getElementById('detail-title');
  var body = document.getElementById('detail-body');

  function chips(entries, kind) {
    if (!entries.length) return '<span class="none">— no file —</span>';

    return entries.map(function (e) {
      var labelHtml = escapeHtml(e.label);

      if (typeof e.colors !== 'undefined' && typeof e.gap !== 'undefined') {
        labelHtml += ' · ' + e.colors + 'c <span style="color:var(--amber)">+' + formatGap(e.gap) + '</span>';
      }

      return '<span class="chip" data-run="' + escapeHtml(e.run_id) +
             '" data-kind="' + kind + '">' + labelHtml + '</span>';
    }).join('');
  }

  function render(nom) {
    var d = STATS[nom];
    if (!d) return;

    var opt = d.nb_optimal;
    var best = d.nb_best;
    var nonOpt = d.nb_non_optimal;

    var pct = TOTAL ? (opt / TOTAL * 100).toFixed(1) : '0.0';
    var pctB = TOTAL ? (best / TOTAL * 100).toFixed(1) : '0.0';
    var pctN = TOTAL ? (nonOpt / TOTAL * 100).toFixed(1) : '0.0';

    title.textContent = nom;

    body.innerHTML =
      '<div class="dk">Total colors spent  ·  ' + d.total_colors + '</div>' +
      '<div class="dk">Total gap to χ  ·  ' + d.total_gap + '</div>' +
      '<div class="dk">Total time  ·  ' + d.total_time + ' ms</div>' +
      '<div class="dk">Optimal  ·  ' + opt + ' / ' + TOTAL + '  (' + pct + ' %)</div>' +
      '<div class="chips">' + chips(d.optimal, 'optimal') + '</div>' +
      '<div class="dk">Best  ·  ' + best + ' / ' + TOTAL + '  (' + pctB + ' %)</div>' +
      '<div class="chips">' + chips(d.best, 'best') + '</div>' +
      '<div class="dk">Non-optimal  ·  ' + nonOpt + ' / ' + TOTAL + '  (' + pctN + ' %)</div>' +
      '<div class="chips">' + chips(d.non_optimal, 'non_optimal') + '</div>';

    rows.forEach(function (tr) {
      tr.classList.toggle('active', tr.dataset.algo === nom);
    });

    body.querySelectorAll('.chip').forEach(function (chip) {
      chip.addEventListener('click', function () {
        showGraph(chip.dataset.run);
      });
    });
  }

  rows.forEach(function (tr) {
    tr.addEventListener('click', function () { render(tr.dataset.algo); });
  });

  // --- graph visualization ---
  var overlay = document.getElementById('modal-overlay');
  var modalBody = document.getElementById('modal-body');
  var modalTitle = document.getElementById('modal-title');
  var modalMeta = document.getElementById('modal-meta');

  function showGraph(runId) {
    var g = GRAPHS[runId];
    if (!g) return;

    document.querySelectorAll('.chip').forEach(function (c) {
      c.classList.toggle('active', c.dataset.run === runId);
    });

    var chi = Number(g.chi || 0);
    var params = g.params || {};
    var paramsStr = Object.keys(params).map(function (k) {
      return k + '=' + params[k];
    }).join(', ');

    modalTitle.textContent = 'Graph ' + runId + ' — ' + (g.graph_type || 'unknown');
    modalMeta.innerHTML = 'χ = <b>' + chi + '</b> · ' + g.n_vertices + ' vertices · ' +
                          g.n_edges + ' edges · density <b>' + Number(g.density || 0).toFixed(3) +
                          '</b> · params <b>' + escapeHtml(paramsStr) + '</b>';

    var results = g.results || {};

    var tableHtml = '<table class="modal-table"><thead><tr><th>Algorithm</th>' +
                    '<th>Colors</th><th>Gap</th><th>Verdict</th><th>Time (ms)</th></tr></thead><tbody>';

    for (var i = 0; i < ALGOS.length; i++) {
      var dispName = ALGOS[i][0], jsonName = ALGOS[i][1];
      var r = results[jsonName];
      if (!r) continue;

      var isBest = (jsonName === g.best_algorithm);
      var gap = safeGap(g, r);
      var isOpt = Boolean(r.optimal) || (chi > 0 && Number(r.n_colors || 0) === chi);

      var verdict = isOpt
        ? '<span class="ok">✓ optimal</span>'
        : '<span class="ko">✗ +' + formatGap(gap) + '</span>';

      var star = isBest ? ' <span class="star">★</span>' : '';

      tableHtml += '<tr class="' + (isBest ? 'best' : '') + '">' +
                   '<td class="algo-name">' + escapeHtml(dispName) + star + '</td>' +
                   '<td>' + Number(r.n_colors || 0) + '</td>' +
                   '<td>+' + formatGap(gap) + '</td>' +
                   '<td>' + verdict + '</td>' +
                   '<td>' + Number(r.time_ms || 0).toFixed(2) + '</td></tr>';
    }

    tableHtml += '</tbody></table>';

    var cardsHtml = '<div class="grid">';
    var cardIdx = 0;

    for (var i = 0; i < ALGOS.length; i++) {
      var dispName = ALGOS[i][0], jsonName = ALGOS[i][1];
      var r = results[jsonName];
      if (!r) continue;

      var isBest = (jsonName === g.best_algorithm);
      var badge = isBest ? ' <span class="badge">best</span>' : '';
      var svg = drawGraph(g.adjacency, r.solution);

      cardsHtml += '<figure class="card' + (isBest ? ' best' : '') +
                   '" style="--i:' + cardIdx + '">' +
                   '<figcaption><span><b>' + escapeHtml(dispName) + '</b>' + badge + '</span>' +
                   '<span>' + Number(r.n_colors || 0) + ' col · ' + Number(r.time_ms || 0).toFixed(2) + ' ms</span></figcaption>' +
                   '<div class="svg-wrap">' + svg + '<div class="gtip"></div></div>' +
                   '<div class="panel-line">χ̂ <b>' + Number(r.n_colors || 0) + '</b> colors · t <b>' +
                   Number(r.time_ms || 0).toFixed(2) + '</b> ms</div></figure>';

      cardIdx++;
    }

    cardsHtml += '</div>';

    modalBody.innerHTML = tableHtml + cardsHtml;

    modalBody.querySelectorAll('.graph-svg').forEach(function (svg) {
      var card = svg.closest('.card');
      attachHover(svg, card);
    });

    overlay.classList.add('show');
    document.body.style.overflow = 'hidden';
  }

  document.getElementById('modal-close').addEventListener('click', closeModal);

  overlay.addEventListener('click', function (e) {
    if (e.target === overlay) closeModal();
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closeModal();
  });

  function closeModal() {
    overlay.classList.remove('show');
    document.body.style.overflow = '';
    document.querySelectorAll('.chip').forEach(function (c) {
      c.classList.remove('active');
    });
  }

  if (rows.length) render(rows[0].dataset.algo);
})();
"""


# ---------------------------------------------------------------------------
# Génération de la page stats.html
# ---------------------------------------------------------------------------

def find_project_root(start_path):
    current = os.path.abspath(start_path)
    while current != os.path.dirname(current):
        if os.path.exists(os.path.join(current, ".gitignore")) or \
           os.path.exists(os.path.join(current, "README.md")):
            return current
        current = os.path.dirname(current)
    return None


def main():
    directory = os.path.dirname(os.path.abspath(__file__))
    project_root = find_project_root(directory)

    if project_root:
        # Relative to the project root so the generated stats.html works
        # wherever the project is downloaded / moved.
        source_dir = os.path.relpath(directory, project_root)
    else:
        # Fallback: relative to the script's own folder.
        source_dir = os.path.relpath(directory, os.path.dirname(os.path.abspath(__file__)))

    json_paths = scanner(directory)

    if not json_paths:
        print(f"No JSON file found in: {directory}")
        sys.exit(1)

    optimal_files = defaultdict(list)
    best_files = defaultdict(list)
    non_optimal_files = defaultdict(list)

    total_colors = defaultdict(int)
    total_time = defaultdict(float)
    total_gap = defaultdict(float)

    aeb_optimal = []
    aeb_best = []
    aeb_non_optimal = []

    graphs = {}

    type_counts = defaultdict(int)
    density_data = defaultdict(list)
    size_counts = defaultdict(int)

    density_algo_stats = defaultdict(lambda: defaultdict(lambda: {"optimal": 0, "best": 0, "total": 0}))
    density_aeb_stats = defaultdict(lambda: {"optimal": 0, "best": 0, "total": 0})

    all_chis = []
    all_vertices = []
    all_densities = []

    for path in json_paths:
        info = analyser_json(path)

        run_id = info["run_id"]
        chi = info["chi"]
        n_vertices = info["n_vertices"]
        n_edges = info["n_edges"]
        density = info["density"]
        graph_type = info["graph_type"] or "unknown"

        adj_int = [[int(c) for c in row] for row in info["adjacency"]]

        graphs[run_id] = {
            "chi": chi,
            "n_vertices": n_vertices,
            "n_edges": n_edges,
            "density": round(density, 4),
            "graph_type": graph_type,
            "params": info["params"],
            "adjacency": adj_int,
            "results": info["results"],
            "best_algorithm": info["best_algorithm"],
            "optimal_algorithms": info["optimal_algorithms"],
            "n_optimal_algorithms": info["n_optimal_algorithms"],
            "best_n_colors": info["best_n_colors"],
        }

        type_counts[graph_type] += 1

        all_chis.append(chi)
        all_vertices.append(n_vertices)
        all_densities.append(density)

        dcat = _density_category(density)
        density_data[dcat].append((run_id, chi, n_edges, density))

        scat = _size_category(n_vertices)
        size_counts[scat] += 1

        min_colors = min(
            (r["n_colors"] for r in info["results"].values() if r["n_colors"] >= 0),
            default=float("inf"),
        )

        for disp_name, json_name in ALGORITHMS:
            r = info["results"].get(json_name)
            if r is None:
                continue

            n_colors = r["n_colors"]
            time_ms = r["time_ms"]
            gap_to_chi = r["gap_to_chi"]

            # Ignore timeouts/errors (n_colors < 0) in aggregates
            if n_colors >= 0:
                total_colors[disp_name] += n_colors
                total_gap[disp_name] += gap_to_chi
            total_time[disp_name] += time_ms

            is_opt = bool(r["optimal"])
            is_best = (min_colors != float("inf") and n_colors == min_colors)

            entry = {
                "run_id": run_id,
                "label": run_id,
                "colors": n_colors,
                "gap": gap_to_chi,
            }

            if is_opt:
                optimal_files[disp_name].append(entry)
            else:
                non_optimal_files[disp_name].append(entry)

            if is_best:
                best_files[disp_name].append(entry)

            # Ignore timeouts/errors in density stats
            if n_colors >= 0:
                density_algo_stats[dcat][disp_name]["total"] += 1
                if is_opt:
                    density_algo_stats[dcat][disp_name]["optimal"] += 1
                if is_best:
                    density_algo_stats[dcat][disp_name]["best"] += 1

        # "The first ten"
        aeb_has_optimal = False
        aeb_has_best = False
        first_ten_best = None

        for json_name in FIRST_TEN_ALGOS:
            r = info["results"].get(json_name)
            if r is None:
                continue

            if r["optimal"]:
                aeb_has_optimal = True

            if min_colors != float("inf") and r["n_colors"] == min_colors:
                aeb_has_best = True

            candidate = (r["n_colors"], r["gap_to_chi"], r["time_ms"])
            if first_ten_best is None or candidate < first_ten_best:
                first_ten_best = candidate

        if first_ten_best is not None:
            aeb_entry = {
                "run_id": run_id,
                "label": run_id,
                "colors": first_ten_best[0],
                "gap": first_ten_best[1],
            }

            density_aeb_stats[dcat]["total"] += 1

            if aeb_has_optimal:
                aeb_optimal.append(aeb_entry)
                density_aeb_stats[dcat]["optimal"] += 1
            else:
                aeb_non_optimal.append(aeb_entry)

            if aeb_has_best:
                aeb_best.append(aeb_entry)
                density_aeb_stats[dcat]["best"] += 1

    total = len(json_paths)

    stats = {}
    rows_html = ""
    barres = []

    for disp_name, json_name in ALGORITHMS:
        ent_opt = sorted(optimal_files[disp_name], key=lambda e: e["run_id"])
        ent_best = sorted(best_files[disp_name], key=lambda e: e["run_id"])
        ent_non = sorted(non_optimal_files[disp_name], key=lambda e: e["run_id"])

        nb_opt = len(ent_opt)
        nb_best = len(ent_best)
        nb_non = len(ent_non)

        pct_opt = nb_opt / total * 100 if total else 0.0
        pct_best = nb_best / total * 100 if total else 0.0
        pct_non = nb_non / total * 100 if total else 0.0

        barres.append((disp_name, round(pct_opt, 1)))

        tc = total_colors[disp_name]
        tt = total_time[disp_name]
        tg = round(total_gap[disp_name], 2)

        stats[disp_name] = {
            "optimal": ent_opt,
            "best": ent_best,
            "non_optimal": ent_non,
            "nb_optimal": nb_opt,
            "nb_best": nb_best,
            "nb_non_optimal": nb_non,
            "total_colors": tc,
            "total_gap": tg,
            "total_time": round(tt, 2),
        }

        esc = html_mod.escape

        rows_html += (
            f'<tr data-algo="{esc(disp_name, quote=True)}">'
            f'<td class="algo-name">{esc(disp_name)}<span class="arrow">▲ view</span></td>'
            f'<td class="num">{nb_opt}</td>'
            f'<td class="num pct"><span class="bar" style="width:{pct_opt:.1f}%"></span>'
            f'{pct_opt:.1f} %</td>'
            f'<td class="num">{nb_best}</td>'
            f'<td class="num pct"><span class="bar" style="width:{pct_best:.1f}%"></span>'
            f'{pct_best:.1f} %</td>'
            f'<td class="num">{nb_non}</td>'
            f'<td class="num pct"><span class="bar" style="width:{pct_non:.1f}%"></span>'
            f'{pct_non:.1f} %</td>'
            f'<td class="num">{tc}</td>'
            f'<td class="num">{tg}</td>'
            f'<td class="num">{tt:.2f}</td>'
            f'</tr>'
        )

    aeb_opt_sorted = sorted(aeb_optimal, key=lambda e: e["run_id"])
    aeb_best_sorted = sorted(aeb_best, key=lambda e: e["run_id"])
    aeb_non_sorted = sorted(aeb_non_optimal, key=lambda e: e["run_id"])

    nb_aeb_opt = len(aeb_opt_sorted)
    nb_aeb_best = len(aeb_best_sorted)
    nb_aeb_non = len(aeb_non_sorted)

    pct_aeb_opt = nb_aeb_opt / total * 100 if total else 0.0
    pct_aeb_best = nb_aeb_best / total * 100 if total else 0.0
    pct_aeb_non = nb_aeb_non / total * 100 if total else 0.0

    stats["The first ten"] = {
        "optimal": aeb_opt_sorted,
        "best": aeb_best_sorted,
        "non_optimal": aeb_non_sorted,
        "nb_optimal": nb_aeb_opt,
        "nb_best": nb_aeb_best,
        "nb_non_optimal": nb_aeb_non,
        "total_colors": "—",
        "total_gap": "—",
        "total_time": "—",
    }

    rows_html += (
        f'<tr data-algo="The first ten">'
        f'<td class="algo-name">The first ten<span class="arrow">▲ view</span></td>'
        f'<td class="num">{nb_aeb_opt}</td>'
        f'<td class="num pct"><span class="bar" style="width:{pct_aeb_opt:.1f}%"></span>'
        f'{pct_aeb_opt:.1f} %</td>'
        f'<td class="num">{nb_aeb_best}</td>'
        f'<td class="num pct"><span class="bar" style="width:{pct_aeb_best:.1f}%"></span>'
        f'{pct_aeb_best:.1f} %</td>'
        f'<td class="num">{nb_aeb_non}</td>'
        f'<td class="num pct"><span class="bar" style="width:{pct_aeb_non:.1f}%"></span>'
        f'{pct_aeb_non:.1f} %</td>'
        f'<td class="num">—</td>'
        f'<td class="num">—</td>'
        f'<td class="num">—</td>'
        f'</tr>'
    )

    n_always = sum(
        1 for dn, _ in ALGORITHMS if stats[dn]["nb_optimal"] == total and total > 0
    )

    algo_names = [dn for dn, _ in ALGORITHMS if dn in stats]
    best_overall = max(algo_names, key=lambda n: stats[n]["nb_best"]) if algo_names else "—"

    date_readable = datetime.now().strftime("%Y-%m-%d at %H:%M:%S")

    avg_chi = sum(all_chis) / len(all_chis) if all_chis else 0
    chi_min = min(all_chis) if all_chis else 0
    chi_max = max(all_chis) if all_chis else 0

    v_min = min(all_vertices) if all_vertices else 0
    v_max = max(all_vertices) if all_vertices else 0

    avg_density = sum(all_densities) / len(all_densities) if all_densities else 0

    n_types = len(type_counts)

    type_cards = ""
    for gtype, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        pct_t = count / total * 100 if total else 0
        type_cards += (
            f'<div class="cat-card"><span class="clabel">{html_mod.escape(gtype)}</span>'
            f'<span class="cval">{count}</span>'
            f'<span class="csub">{pct_t:.1f}%</span></div>'
        )

    density_rows = ""
    for cat_name, lo, hi in DENSITY_CATEGORIES:
        entries = density_data.get(cat_name, [])
        count = len(entries)
        pct_d = count / total * 100 if total else 0

        if entries:
            edge_min = min(e[2] for e in entries)
            edge_max = max(e[2] for e in entries)
            avg_c = sum(e[1] for e in entries) / len(entries)
        else:
            edge_min = edge_max = 0
            avg_c = 0

        range_str = f"{lo:.2f} – {hi:.2f}" if hi <= 1.0 else f"{lo:.2f} – 1.00"

        density_rows += (
            f'<tr><td class="algo-name">{cat_name}</td>'
            f'<td class="num">{range_str}</td>'
            f'<td class="num">{count}</td>'
            f'<td class="num pct"><span class="bar" style="width:{pct_d:.1f}%"></span>'
            f'{pct_d:.1f} %</td>'
            f'<td class="num">{edge_min} – {edge_max}</td>'
            f'<td class="num">{avg_c:.1f}</td>'
            f'<td class="num"><div class="density-bar"><div class="track">'
            f'<div class="fill" style="width:{pct_d:.1f}%"></div></div>'
            f'<span class="val">{count}</span></div></td></tr>'
        )

    size_cards = ""
    for cat_name, lo, hi in SIZE_CATEGORIES:
        count = size_counts.get(cat_name, 0)
        if count > 0:
            pct_s = count / total * 100 if total else 0
            size_cards += (
                f'<div class="cat-card"><span class="clabel">{cat_name}</span>'
                f'<span class="cval">{count}</span>'
                f'<span class="csub">{pct_s:.1f}%</span></div>'
            )

    density_algo_rows = ""
    for cat_name, lo, hi in DENSITY_CATEGORIES:
        cat_total = len(density_data.get(cat_name, []))
        if cat_total == 0:
            continue

        for disp_name, json_name in ALGORITHMS:
            s = density_algo_stats[cat_name].get(disp_name, {"optimal": 0, "best": 0, "total": 0})
            n_opt = s["optimal"]
            n_best = s["best"]

            pct_o = n_opt / cat_total * 100 if cat_total else 0
            pct_b = n_best / cat_total * 100 if cat_total else 0

            density_algo_rows += (
                f'<tr><td class="algo-name">{cat_name}</td>'
                f'<td class="num">{cat_total}</td>'
                f'<td class="algo-name">{html_mod.escape(disp_name)}</td>'
                f'<td class="num">{n_opt}/{cat_total}</td>'
                f'<td class="num pct"><span class="bar" style="width:{pct_o:.1f}%"></span>'
                f'{pct_o:.1f} %</td>'
                f'<td class="num">{n_best}/{cat_total}</td>'
                f'<td class="num pct"><span class="bar" style="width:{pct_b:.1f}%"></span>'
                f'{pct_b:.1f} %</td></tr>'
            )

        s = density_aeb_stats.get(cat_name, {"optimal": 0, "best": 0, "total": 0})
        n_opt = s["optimal"]
        n_best = s["best"]

        pct_o = n_opt / cat_total * 100 if cat_total else 0
        pct_b = n_best / cat_total * 100 if cat_total else 0

        density_algo_rows += (
            f'<tr><td class="algo-name">{cat_name}</td>'
            f'<td class="num">{cat_total}</td>'
            f'<td class="algo-name">The first ten</td>'
            f'<td class="num">{n_opt}/{cat_total}</td>'
            f'<td class="num pct"><span class="bar" style="width:{pct_o:.1f}%"></span>'
            f'{pct_o:.1f} %</td>'
            f'<td class="num">{n_best}/{cat_total}</td>'
            f'<td class="num pct"><span class="bar" style="width:{pct_b:.1f}%"></span>'
            f'{pct_b:.1f} %</td></tr>'
        )

    body = f"""<div class="page">
<header>
  <div>
    <h1>Algorithm statistics</h1>
    <div class="meta">generated on <b>{date_readable}</b> · directory <b>{html_mod.escape(os.path.basename(directory))}</b> · <b>{total}</b> JSON files analysed</div>
  </div>
  <div class="chi-badge" title="Number of JSON files analysed">
    <span class="k">files</span><span class="v">{total}</span>
  </div>
</header>

<div class="banner">
  <div class="bitem"><span class="bk">Algorithms</span><span class="bv">{len(ALGORITHMS)}</span></div>
  <div class="bitem" title="Algorithms that reached χ on every file">
    <span class="bk">Always optimal</span><span class="bv">{n_always}</span></div>
  <div class="bitem"><span class="bk">Best overall</span><span class="bv">{html_mod.escape(best_overall)} <span class="star">★</span></span></div>
  <div class="bitem"><span class="bk">Graph types</span><span class="bv">{n_types}</span></div>
  <div class="bitem" title="Average chromatic number across all graphs">
    <span class="bk">Avg χ</span><span class="bv">{avg_chi:.1f}</span></div>
  <div class="bitem" title="Min – Max chromatic number">
    <span class="bk">χ range</span><span class="bv">{chi_min}–{chi_max}</span></div>
  <div class="bitem" title="Min – Max vertices across all graphs">
    <span class="bk">Vertices range</span><span class="bv">{v_min}–{v_max}</span></div>
  <div class="bitem" title="Average edge density across all graphs">
    <span class="bk">Avg density</span><span class="bv">{avg_density:.3f}</span></div>
</div>

<section>
  <h2>Graph distribution by type <span class="hint">type of each graph from JSON</span></h2>
  <div class="cat-grid">{type_cards}</div>
</section>

<section>
  <h2>Graph distribution by edge density <span class="hint">density = m / (n·(n-1)/2)</span></h2>
  <table id="density-table">
    <thead><tr><th>Density category</th><th>Density range</th><th>Graphs</th><th>%</th><th>Edge range</th><th>Avg χ</th><th>Distribution</th></tr></thead>
    <tbody>{density_rows}</tbody>
  </table>
</section>

<section>
  <h2>Graph distribution by size <span class="hint">number of vertices</span></h2>
  <div class="cat-grid">{size_cards}</div>
</section>

<section>
  <h2>Algorithm performance per density category <span class="hint">% optimal and % best for each algorithm</span></h2>
  <table id="density-algo-table">
    <thead><tr><th>Density category</th><th>Graphs</th><th>Algorithm</th><th>Optimal</th><th>% optimal</th><th>Best</th><th>% best</th></tr></thead>
    <tbody>{density_algo_rows}</tbody>
  </table>
  <div class="hint" style="margin-top:12px;font-size:.72rem;color:var(--muted);font-style:italic">
    💡 <b>The first ten</b> = the 10 first algorithms of the portfolio (greedy … tabu)
  </div>
</section>

<section>
  <h2>Optimality per algorithm <span class="hint">click a row to see the files where it was optimal — click a file to draw the graph</span></h2>

  <div class="union-bar">
    <button class="union-btn" id="union-btn">⚡ Union</button>
    <span class="union-status" id="union-status">Select algorithms to compute the union of their optimal files</span>
  </div>

  <div class="union-panel" id="union-panel">
    <h3>Select algorithms — the union of their optimal files will be computed</h3>
    <div class="union-algos" id="union-algos"></div>

    <div class="union-source">
      <label for="source-dir-input">Source directory of JSON files</label>
      <input type="text" id="source-dir-input" class="source-dir-input" value="">
      <div class="hint">Change this path if you downloaded the project on another machine.</div>
    </div>

    <div class="union-dest">
      <label for="dest-dir-input">Copy destination directory</label>
      <input type="text" id="dest-dir-input" class="dest-dir-input" value="">
      <div class="hint">Leave empty to copy into the current directory, or enter the folder where the files will be copied.</div>
    </div>

    <div class="union-actions">
      <button class="union-action primary" id="union-compute">Compute union</button>
      <button class="union-action" id="union-clear">Clear</button>
      <button class="union-action" id="union-close">Close</button>
      <button class="union-action" id="export-ids-btn">📋 Copy IDs (optimal)</button>
      <button class="union-action" id="export-script-btn">📦 Export script (optimal)</button>
      <button class="union-action" id="export-ids-non-btn">📋 Copy IDs (non-optimal)</button>
      <button class="union-action" id="export-script-non-btn">📦 Export script (non-optimal)</button>
      <button class="union-action" id="export-script-bat-btn">📦 Export .bat (optimal)</button>
      <button class="union-action" id="export-script-bat-non-btn">📦 Export .bat (non-optimal)</button>
    </div>

    <div class="union-result" id="union-result"></div>
  </div>

  <div class="explain">
    <div class="ex-title">What does “optimal” mean?</div>
    <p>Each algorithm colors the graph and returns a number of colors. The <b>optimal</b> value is the <b>minimum number of colors</b> found across all algorithms on the same graph.</p>
    <ul>
      <li>When <b>Backtracking (exact)</b> is present, it computes the true chromatic number χ — the optimal is then <b>absolute</b> (mathematically proven).</li>
      <li>When <b>Backtracking is absent</b>, the optimal becomes the <b>best heuristic solution</b> — the minimum found by the 10 first algorithms. It is an approximation, not a proof.</li>
      <li class="ex-note">⚠ In that case, <b>The first ten</b> always reaches 100% optimality, because it is defined as “at least one of the 10 first algorithms found the minimum” — and the minimum is by definition found by at least one of them.</li>
    </ul>
  </div>

  <table id="algo-table">
    <thead><tr><th>Algorithm</th><th>Optimal</th><th>% optimal</th><th>Best</th><th>% best</th><th>Non-optimal</th><th>% non-optimal</th><th>Total colors</th><th>Total gap</th><th>Total time (ms)</th></tr></thead>
    <tbody>{rows_html}</tbody>
  </table>

  <div class="hint" style="margin-top:12px;font-size:.72rem;color:var(--muted);font-style:italic">
    💡 <b>The first ten</b> = the 10 first algorithms of the portfolio (greedy … tabu)
  </div>
</section>

<section class="detail" id="detail">
  <h2 id="detail-title">Select an algorithm</h2>
  <div class="detail-body" id="detail-body"></div>
</section>

<footer>Strategies for Optimal Graph Coloring · statistics generated by html_stats.py from JSON data</footer>
</div>

<div class="modal-overlay" id="modal-overlay">
  <div class="modal">
    <div class="modal-header">
      <div>
        <h3 id="modal-title">Graph</h3>
        <div class="meta" id="modal-meta"></div>
      </div>
      <button class="modal-close" id="modal-close">✕ Close</button>
    </div>
    <div class="modal-body" id="modal-body"></div>
  </div>
</div>"""

    safe_lt = "\\u003c"

    json_stats = json.dumps(stats, ensure_ascii=False).replace("<", safe_lt)
    json_graphs = json.dumps(graphs, ensure_ascii=False).replace("<", safe_lt)
    json_algos = json.dumps(ALGORITHMS, ensure_ascii=False).replace("<", safe_lt)

    script = (SCRIPT
              .replace("__STATS__", json_stats)
              .replace("__GRAPHS__", json_graphs)
              .replace("__ALGOS__", json_algos)
              .replace("__TOTAL__", str(total))
              .replace("__SOURCE_DIR__", json.dumps(source_dir)))

    html_out = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Statistics — algorithm optimality</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>{STYLE}</style>
</head>
<body>
{body}
<script>{script}</script>
</body>
</html>
"""

    out_path = os.path.join(directory, "stats.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_out)

    print(f"✓ {total} JSON file(s) analysed in: {directory}")
    print(f"✓ Statistics generated: {out_path}")
    print()
    print(f"  {'Algorithm':<24}{'Optimal':>9}{'%':>9}{'Best':>7}{'%':>8}{'Gap':>8}{'Colors':>9}{'Time (ms)':>12}")
    print("  " + "-" * 84)

    for nom, pct in barres:
        d = stats[nom]
        gap_str = str(d['total_gap']) if isinstance(d['total_gap'], str) else f"{d['total_gap']:.1f}"
        print(f"  {nom:<24}{d['nb_optimal']:>9}{pct:>8.1f}%{d['nb_best']:>7}{pct:>7.1f}%{gap_str:>8}{d['total_colors']:>9}{d['total_time']:>12.2f}")

    print()


if __name__ == "__main__":
    main()
