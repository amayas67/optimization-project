# Experimental Analysis Infrastructure for Graph Coloring

**Author:** Amayas AZIZ — M2 Student, UMMTO
**GitHub:** https://github.com/amayas67 · **Contact:** amayasaziz6700@gmail.com

A complete, modular, and reproducible digital laboratory for graph coloring.
Each experiment generates a graph, runs the full solver portfolio, verifies
optimality via exact methods, and exports a self-describing JSON ready for
Machine Learning.

- **13 solvers** — Greedy, Welsh-Powell, DSATUR, IDO, RLF, Smallest-Degree-Last,
  Random Greedy (×10), Simulated Annealing, Tabucol, HEA, and the exact
  Backtracking, CP-SAT (OR-Tools) and SAT.
- **11 graph families** — Erdős–Rényi, bipartite, complete, multipartite, tree,
  regular, cycle, wheel, 2D grid, hypercube, Mycielski.
- **Exact ground truth** — backtracking / CP-SAT / SAT give a provable chromatic
  number χ; heuristics are measured against it via `gap_to_χ`.
- **Reproducible** — fix one `SEED` in `main.py` and the whole corpus regenerates
  identically (graph = SEED + run index).
- **ML-ready JSON** — each instance packs the adjacency matrix, structural
  features (density, degrees, girth, ω-lower-bound, …), χ, per-solver results
  and labels.

---

## The Framework

A modular digital laboratory for graph coloring. Each experiment generates a
graph, runs all solvers, verifies optimality via exact backtracking, and exports
a self-describing JSON ready for analysis.

| | |
|---|---|
| **Implemented Algorithms** | 13 solvers (construction, stochastic, metaheuristics, exact) |
| **Graph Generators** | 11 types (random, bipartite, complete, multipartite, tree, regular, cycle, wheel, 2D grid, hypercube, Mycielski) |
| **Automated Pipeline** | Controlled seed · 296 iterations per run · sequential JSON export (000001.json…) · flat structural features (ML-ready) |
| **Optimality Verification** | Exact backtracking → proven optimal χ · heuristic fallback if backtracking too slow · auto labels: `best_algorithm`, `optimal_algorithms`, `gap_to_χ` |
| **Integrated Analysis** | `html_stats.py` (interactive report), `json_stats.py` (text), `full_report.py` (aggregation), SVG hover visualization + export copy scripts |
| **ML / Research Ready** | `load_data()` → pandas DataFrame ("long" or "wide") · features: density, degrees, girth, ω-lower-bound, bipartite, components, degree sequence |

### Algorithm reference

| Algorithm | Category | Complexity / Nature | Key Parameters | Status |
|---|---|---|---|---|
| Greedy | Construction | O(n+m) — natural order | — | Core |
| Welsh-Powell | Construction | O(n log n) — descending degree | — | Core |
| DSATUR | Construction | O(n²) — saturation degree | — | Core |
| IDO | Construction | O(n²) — incidence degree | — | Core |
| RLF | Construction | O(n²) — independent sets | — | Core |
| Smallest-Degree-Last | Construction | O(n+m) — degeneracy order | — | Core |
| Random Greedy (×10) | Stochastic | O(10·(n+m)) — multi-start | trials=10 | Core |
| Simulated Annealing | Metaheuristic | Stochastic — cooling | max_iter=20000 | Meta |
| Tabucol | Metaheuristic | Tabu search — conflicts | max_iter=20000 | Meta |
| HEA | Hybrid (GA+TS) | Evolutionary — GPX crossover + Tabu | pop=10, gen=50, ls=1000 (main) / pop=5, gen=10, ls=100 (challenging) | Meta |
| Backtracking (exact) | Exact | Exponential — Welsh-Powell pruning | — | Exact |
| CP-SAT (OR-Tools) | Exact (CP) | Constraint programming | time_limit=60s (capped at 60/k per k) | Exact |
| SAT | Exact (SAT) | SAT reduction + solver | — | Exact |

#### Detailed operation of each algorithm

- **Greedy** — Traverses vertices in natural order (0, 1, …, n−1) and assigns each
  vertex the smallest color not used by its already-colored neighbors.
  *Complexity:* O(n+m). Very fast but quality depends on vertex order.
  *Usage:* baseline, initial upper bound, component of other algorithms.

- **Welsh-Powell** — Sorts vertices by descending degree before applying greedy
  coloring. High-degree vertices (more constraining) are colored first.
  *Complexity:* O(n log n + m). Significantly improves naive greedy on most graphs.

- **DSATUR** (Brélaz, 1979) — At each step, selects the uncolored vertex with the
  maximal *saturation degree* (number of distinct colors among its neighbors). Ties
  broken by maximal total degree. *Complexity:* O(n²). One of the best deterministic
  heuristics; often optimal on sparse graphs.

- **IDO** (Incidence Degree Ordering) — DSATUR variant: selects the vertex with the
  largest *incidence degree* (number of already-colored neighbors, not distinct
  colors). Ties broken by total degree. IDO counts colored neighbors (quantity),
  DSATUR counts distinct colors (quality). *Complexity:* O(n²).

- **RLF** (Recursive Largest First, Leighton 1979) — Builds one color at a time by
  forming a *maximal independent set*: starts from a vertex, iteratively adds the
  non-adjacent vertex with the most neighbors in the set under construction. Repeats
  on the remaining subgraph. *Complexity:* O(n²). Excellent on dense graphs; often
  close to optimal.

- **Smallest-Degree-Last (SDL)** (Matula & Beck, 1983) — Iteratively removes the
  *minimum-degree* vertex in the remaining subgraph, recording the removal order.
  Then colors in reverse order (last removed first). *Complexity:* O(n+m) with a
  bucket queue. The degeneracy order guarantees χ ≤ k+1 where k is the degeneracy.

- **Random Greedy (×10)** — Runs greedy coloring 10 times on a *random vertex order*
  (different seed each trial). Keeps the best result (fewest colors).
  *Complexity:* O(10·(n+m)). Simple stochastic baseline; explores the vertex-order space.

- **Simulated Annealing (SA)** — Starts from an initial coloring (greedy), then
  explores the coloring space via *local moves* (recoloring a vertex). Accepts
  worsening moves with a probability that decreases according to a *temperature
  schedule* (cooling). *Key parameters:* max_iter=20000, initial temperature=10.0,
  cooling_rate=0.999, min_temp=0.01. Can escape local optima; quality depends on the
  schedule and allocated time.

- **Tabucol** (Hertz & de Werra, 1987) — Tabu search for k-coloring: works on
  *conflicts* (monochromatic edges). At each iteration, chooses the best non-tabu move
  (recoloring a conflicting vertex) that most reduces conflicts. Uses a *tabu list*
  (adaptive tenure) to forbid immediate returns. *Key parameters:* max_iter=20000,
  tenure = floor(0.6·|conflicts|) + randint(0, 9). Very effective at finding a valid
  k-coloring if k ≥ χ; basis of HEA.

- **HEA (Hybrid Evolutionary Algorithm)** (Galinier & Hao, 1999) — Memetic algorithm:
  *Population* of valid k-colorings + *GPX crossover* (Greedy Partition Crossover)
  that assembles the best color classes of two parents + *Tabucol local search* on
  each child. Loop: tournament selection → GPX → Tabucol (ls_iter) → replace most
  similar parent if child is better. *Parameters:* pop_size=10, max_generations=50,
  ls_iter=1000 (decreases k while a valid solution is found). Reference method;
  combines global exploration (GA) and local exploitation (Tabu).

- **Backtracking (exact)** — Exhaustive search with pruning: tries to assign colors
  to vertices (Welsh-Powell order: descending degree) via backtracking. Cuts a branch
  as soon as the number of colors used ≥ best solution found. *Complexity:*
  exponential in the worst case; fast on small/medium or structured graphs. Provides
  *proven optimal* χ (ground truth) for the benchmark.

- **CP-SAT (OR-Tools)** — Models coloring as a CSP: variables = color of each vertex
  (domain 0..k−1), constraints = adjacent vertices ≠ color. Solved by *CP-SAT*
  (Google OR-Tools): tree search + constraint propagation + clause learning. Iterates
  k = 1..upper_bound (greedy); stops at the first k with status=OPTIMAL. *Parameters:*
  time_limit=60s, but per-k budget is capped at min(60, 60/k) seconds.

- **SAT** — Reduction of k-coloring to *SAT*: boolean variables x<sub>v,c</sub> (vertex
  v has color c). Constraints: (1) each vertex has at least one color, (2) at most one
  color per vertex, (3) adjacent vertices do not share the same color. Solved with a
  SAT solver (e.g. Glucose, CaDiCaL). Incremental (descending) search over k; a hard
  process-level timeout is enforced by the runner on the challenging subset.

---

## Laboratory Toolkit

The lab is a reproducible pipeline. Each step reads/writes self-describing JSON so
that everything can be re-run, compared, and extracted without a database.

**Setup (optional, only for CP-SAT / SAT / ML):**
`pip install -r requirements.txt` (installs `ortools`, `python-sat`, `pandas`).

### Tools at a glance

| Script | Role |
|---|---|
| `main.py` | Generate graphs (Mode A) or re-run solvers on existing JSON into `update/` (Mode B); export ML-ready JSON |
| `html_stats.py` | Interactive HTML report (optimality, per-file graph drawing, Union / Extract / Compare) |
| `json_stats.py` | Plain-text statistics → `json_stats_results.txt`, plus the "first ten" heuristic group summary |
| `full_report.py` | Aggregate per-size HTML reports (copies each `<n>_vertices/stats.html` into `full_report/`, prefixed by size) |
| `load_data()` | Load the corpus into a pandas DataFrame (long / wide): features (X), labels (`best_algorithm`, `optimal`, `gap_to_χ`) |
| `no_redondance.py` | Deduplicate JSON by adjacency matrix (→ `unique/`) |
| `delete_report.py` | Wipe all html/json inside `results/` (use with care) |

### `main.py` — configuration & usage

Two modes are selected by the `operate_on_existing_json` flag at the top of the
`if __name__ == "__main__":` block:

- **Mode A — Generation** (`operate_on_existing_json = 0`): generates `loop_nb`
  graphs of type `generate` (1 = random … 11 = mycielski) using `PARAMS`, runs every
  solver listed in `ALGORITHMS`, and exports one JSON per graph into
  `results/json/<type>/<run_id>.json` (sequential 000001.json…).

- **Mode B — JSON re-run** (`operate_on_existing_json = 1`): scans `JSON_DIR`
  (e.g. `results/json/random/`); for each `*.json` it recomputes **only the enabled
  algorithms that are missing** from the file (present ones are kept untouched),
  drops those listed in `DEL_ALGORITHME`, recomputes χ and the labels, and writes the
  result into `results/json/<type>/update/`. **The originals are never overwritten.**
  If a file already contains all the selected algorithms, it is simply copied as-is
  into `update/` (no recomputation).

**Key knobs:** `SEED` (None = non-reproducible, int = reproducible, graph = SEED +
run index) · `loop_nb` (iterations, generation only) · `generate` + `PARAMS` (which
graph & its parameters) · `ALGORITHMS` (comment a line to disable a solver) ·
`DEL_ALGORITHME` (ids to drop from processed JSON) · `_safe_exact(...)` budget for
exact solvers (`time_limit`, `main_kill`).

**Run:** `python3 graph/exact_coloring/experiment/main.py`

### The Union / Extract / Compare panel (inside `stats.html`)

The interactive report (`stats.html`) has a **⚡ Union** button that opens a panel to
combine, extract, and compare instances across solvers:

- **Union** — select one or more algorithms; the panel computes the *union of files*
  where the selected algorithm(s) reached the optimum (or the non-optimal ones), with
  a per-density breakdown.
- **Compare** — the table shows, for each algorithm, its optimal rate, best rate,
  total colors, total gap, and total time, so solvers can be compared at a glance.
- **Extract** — export the selected set of files:
  - **📋 Copy IDs** — copies the run IDs (e.g. `000024`) to the clipboard;
  - **📦 Export script** — downloads a copy script (`copy_optimal_union.sh` / `.bat`,
    or the non-optimal variants) that copies the chosen JSON files from the source
    folder to a destination folder. Both paths are set directly in the interface.

### Typical workflow

```bash
# from the project root
pip install -r requirements.txt      # ortools, python-sat, pandas (optional)

# 1. (Mode A) Generate a corpus
python3 graph/exact_coloring/experiment/main.py
#    → writes JSON into results/json/<type>/

# 2. (Mode B) Refresh solvers on existing JSON
#    set operate_on_existing_json=1 in main.py, then:
python3 graph/exact_coloring/experiment/main.py
#    → writes processed files to results/json/<type>/update/

# 3. Build the interactive + text reports inside a size folder
cd graph/exact_coloring/experiment/results/json/random/50_vertices
python3 html_stats.py && python3 json_stats.py

# 4. Aggregate per-size reports
python3 graph/exact_coloring/experiment/results/json/random/full_report.py

# 5. Open stats.html → click ⚡ Union to compare / extract instances
```

---

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
