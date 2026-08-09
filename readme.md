# Experimental Analysis Infrastructure for Graph Coloring

A reproducible, modular digital laboratory for **graph coloring**: it generates graphs,
runs a portfolio of solvers, verifies optimality with exact methods, and exports a
self-describing, ML-ready corpus.

## What it does

- **13 solvers** — Greedy, Welsh-Powell, DSATUR, IDO, RLF, Smallest-Degree-Last,
  Random Greedy (×10), Simulated Annealing, Tabucol, HEA, and the exact
  Backtracking, CP-SAT (OR-Tools) and SAT.
- **11 graph families** — Erdős–Rényi, bipartite, complete, multipartite, tree,
  regular, cycle, wheel, 2D grid, hypercube, Mycielski.
- **Exact ground truth** — backtracking / CP-SAT / SAT give a provable chromatic
  number χ; heuristics are measured against it via `gap_to_χ`.
- **Reproducible** — fix one `SEED` in `main.py` and the whole corpus regenerates
  identically (graph = SEED + run index).
- **ML-ready JSON** — each instance packs the adjacency matrix, structural features
  (density, degrees, girth, ω-lower-bound, …), χ, per-solver results and labels.

## Quick start

```bash
pip install -r requirements.txt

# 1. Generate a corpus (writes JSON into results/json/<type>/)
python3 graph/exact_coloring/experiment/main.py

# 2. Re-run solvers & group files by size
python3 graph/exact_coloring/experiment/results/json/random/compare.py

# 3. Build the interactive + text reports inside a size folder
cp graph/exact_coloring/experiment/results/json/random/html_stats.py 60_vertices/
cp graph/exact_coloring/experiment/results/json/random/json_stats.py 60_vertices/
cd 60_vertices && python3 html_stats.py && python3 json_stats.py

# 4. Open stats.html → click "⚡ Union" to compare / extract instances
```

## Toolkit

| Script | Role |
|---|---|
| `main.py` | Generate graphs, run all solvers, export JSON |
| `compare.py` | Re-run solvers on existing JSON, group by size |
| `html_stats.py` | Interactive HTML report (optimality, per-file graph drawing, Union/Extract/Compare) |
| `json_stats.py` | Plain-text statistics |
| `full_report.py` | Aggregate per-size HTML reports |
| `load_data()` | Load the corpus into a pandas DataFrame (long / wide) |

## Findings (highlight)

On ~296 random graphs (n≈60, p≈0.6) the framework isolated **37 hard instances**
where only exact backtracking reaches χ; all heuristics stay stuck at χ+1. The gap
is systematically 1, suggesting a shared structural property near the
k-colorability phase transition.

## Project layout

```
graph/
  generation_graph/        # 11 graph generators
  exact_coloring/
    algo/                  # 13 coloring solvers
    experiment/
      main.py              # main experiment entry point
      results/json/...     # exported JSON corpus + analysis scripts
```

## Author

Amayas AZIZ — M2 Student, UMMTO
GitHub: https://github.com/amayas67
Contact: amayasaziz6700@gmail.com
