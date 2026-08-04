# Exact Coloring

Find the minimum number of colors for a given graph.

## 📁 Structure

```
graph/exact_coloring/
├── algo/                    # Coloring algorithms
│   ├── greedy.py
│   ├── backtrack.py
│   ├── dsatur.py
│   ├── ido.py
│   ├── rlf.py
│   ├── welsh_powell.py
│   ├── smallest_degree_last.py
│   └── random_greedy.py
├── generation_graph/        # Graph generators
│   ├── generate_graph_random.py
│   ├── generate_bipartite.py
│   ├── generate_complet.py
│   ├── generate_cycle.py
│   ├── generate_grid.py
│   ├── generate_hypercube.py
│   ├── generate_multipartite.py
│   ├── generate_mycielski.py
│   ├── generate_regular.py
│   ├── generate_tree.py
│   └── generate_wheel.py
└── experiment/
    ├── main.py              # Runs the experiments
    ├── rapport_html.py      # Generates HTML reports
    ├── stats.py             # Generates statistics
    └── results/
        ├── HTML/            # Generated HTML reports
        └── json/            # Machine-ready JSON data
```

---

## 🧪 Running experiments with `main.py`

### 1. Launch an experiment

```bash
cd graph/exact_coloring/experiment
python main.py
```

### 2. Variables to modify

Open `main.py` and edit the **Configuration** section (lines ~570-635):

| Variable | Description | Example |
|----------|-------------|---------|
| `show` | Display matplotlib figures (`True`/`False`) | `show = False` |
| `layout` | Graph layout (`"circle"` or `"spring"`) | `layout = "circle"` |
| `SEED` | Random seed for reproducibility (`None` = random) | `SEED = 42` |
| `loop_nb` | Number of graphs to generate and color | `loop_nb = 3` |
| `generate` | Graph type to generate (1 to 11) | `generate = 1` |
| `PARAMS` | Graph generation parameters | see below |

### 3. Choosing the graph type

The `generate` variable selects the graph type:

| Value | Type | Parameters (`PARAMS`) |
|-------|------|----------------------|
| 1 | random (Erdős–Rényi) | `{"n": 50, "p": 0.4}` |
| 2 | bipartite | `{"u": 5, "v": 5, "p": 0.5}` |
| 3 | complete | `{"n": 8}` |
| 4 | multipartite | `{"group_sizes": [2, 2, 2]}` |
| 5 | tree | `{"n": 16}` |
| 6 | regular | `{"n": 10, "d": 3}` |
| 7 | cycle | `{"n": 10}` |
| 8 | wheel | `{"n": 10}` |
| 9 | grid | `{"rows": 3, "cols": 4}` |
| 10 | hypercube | `{"d": 3}` |
| 11 | mycielski | `{"k": 4}` |

**Example**: to generate 5 regular graphs with 20 vertices of degree 4:

```python
SEED = 42
loop_nb = 5
generate = 6
PARAMS = {"regular": {"n": 20, "d": 4}}
```

### 4. Including / excluding algorithms

The `ALGORITHMS` list (line ~626) defines which algorithms are executed. **Comment or uncomment** lines to include or exclude an algorithm:

```python
ALGORITHMS = [
    ("greedy",               "Greedy",               lambda g: greedy_coloring(g)),
    ("welsh_powell",         "Welsh-Powell",         lambda g: welsh_powell_coloring(g)),
    ("dsatur",               "DSATUR",               lambda g: dsatur_coloring(g)),
    ("ido",                  "IDO",                  lambda g: ido_coloring(g)),
    ("rlf",                  "RLF",                  lambda g: rlf_coloring(g)),
    ("smallest_degree_last", "Smallest-degree-last", lambda g: smallest_degree_last_coloring(g)),
    ("random_greedy",        "Random greedy (×10)",  lambda g: best_random_greedy_coloring(g, trials=10)),
    ("backtracking",         "Backtracking (exact)", lambda g: backtrack_coloring(g)),
]
```

For example, to keep only DSATUR and RLF:

```python
ALGORITHMS = [
    # ("greedy",               "Greedy",               lambda g: greedy_coloring(g)),
    # ("welsh_powell",         "Welsh-Powell",         lambda g: welsh_powell_coloring(g)),
    ("dsatur",               "DSATUR",               lambda g: dsatur_coloring(g)),
    # ("ido",                  "IDO",                  lambda g: ido_coloring(g)),
    ("rlf",                  "RLF",                  lambda g: rlf_coloring(g)),
    # ("smallest_degree_last", "Smallest-degree-last", lambda g: smallest_degree_last_coloring(g)),
    # ("random_greedy",        "Random greedy (×10)",  lambda g: best_random_greedy_coloring(g, trials=10)),
    # ("backtracking",         "Backtracking (exact)", lambda g: backtrack_coloring(g)),
]
```

> ⚠️ **Important**: `backtracking` is the exact algorithm that computes χ (the chromatic number). If you remove it, the reports cannot determine which algorithms are optimal.

### 5. Adding your own algorithm

1. **Create your file** in `graph/exact_coloring/algo/`, for example `my_algo.py`:

```python
def my_algo_coloring(adj):
    """
    adj : adjacency matrix (list[list[int]])
    Returns : (colors, nb_colors)
      colors    : list[int] — color of each vertex
      nb_colors : int       — number of colors used
    """
    n = len(adj)
    colors = [0] * n
    # ... your coloring logic ...
    return colors, max(colors) + 1
```

2. **Import it** in `main.py` (imports section, line ~53):

```python
from my_algo import my_algo_coloring
```

3. **Add it** to the `ALGORITHMS` list:

```python
ALGORITHMS = [
    # ... existing algorithms ...
    ("my_algo", "My Algorithm", lambda g: my_algo_coloring(g)),
]
```

### 6. Generated results

After each run, `main.py` generates in `results/`:

- **`results/HTML/<type>/000001.html`** — interactive report (comparison table, SVG colorings, optimal/best verdict)
- **`results/json/<type>/000001.json`** — machine-ready data (features, labels, adjacency matrix)

Files are numbered sequentially (`000001`, `000002`, ...).

---

## 📊 Statistics with `stats.py`

### 1. Placing the script

Copy `stats.py` into the directory containing the HTML reports to analyze, **or** pass the path as an argument.

### 2. Running the statistics

```bash
# Option 1: from the reports directory
cd graph/exact_coloring/experiment/results/HTML
python /path/to/stats.py

# Option 2: pass the directory as an argument (recommended)
cd graph/exact_coloring/experiment
python stats.py results/HTML
```

### 3. What `stats.html` produces

The script **recursively** analyzes all `.html` files in the directory and generates `stats.html` with, for each algorithm:

| Column | Description |
|--------|-------------|
| **Optimal** | Number of times the algorithm reached χ (optimal colors) |
| **% optimal** | Corresponding percentage (with progress bar) |
| **Best** | Number of times the algorithm was the best (fewest colors, then shortest time) |
| **% best** | Corresponding percentage |
| **Total colors** | Sum of colors used across all reports |
| **Total time (ms)** | Sum of execution times across all reports |

**Interaction**: click on an algorithm row to display the list of files (run_id) where it was optimal and best. Each file is clickable and opens the corresponding report.

**Example**:

```bash
cd graph/exact_coloring/experiment
python stats.py results/HTML
```

```
✓ 6 HTML report(s) analyzed in : .../results/HTML
✓ Statistics generated : .../results/HTML/stats.html

  Algorithm                 Optimal        %   Best       %   Colors   Time (ms)
  ------------------------------------------------------------------------------
  Greedy                          0     0.0%      0    0.0%       65        3.00
  Welsh-Powell                    0     0.0%      0    0.0%       58        3.17
  DSATUR                          0     0.0%      0    0.0%       55        8.02
  ...
```

Then open `results/HTML/stats.html` in your browser.