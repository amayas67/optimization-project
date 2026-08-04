================================================================================
 README — Graph Coloring Experiment (main.py)
================================================================================

This folder contains the main experiment script for comparing graph
coloring algorithms.

--------------------------------------------------------------------------------
1. WHAT main.py DOES
--------------------------------------------------------------------------------

main.py is the entry point of the experiment. For a chosen graph type it:

  1. generates a graph (an n x n adjacency matrix),
  2. runs every algorithm in the ALGORITHMS list on that graph,
  3. prints a terminal report (colors, gap, optimality, time),
  4. exports a "machine-ready" JSON file into:

         results/json/<graph_type>/<run_id>.json

     (e.g. results/json/random/000001.json)

  The JSON file contains the full adjacency matrix, structural features,
  the ground truth chi, the per-algorithm results (n_colors, gap, optimal,
  time_ms, solution) and precomputed labels — everything needed for machine
  learning or further analysis.

  Run it with:

         python3 main.py

--------------------------------------------------------------------------------
2. CONFIGURATION AT THE TOP OF main.py
--------------------------------------------------------------------------------

Inside the "if __name__ == '__main__':" block (bottom of the file) you can
tune the experiment:

  show = False
      False -> no matplotlib window (recommended for batch runs)
      True  -> opens an interactive colored graph for each algorithm

  layout = "circle"
      "circle" or "spring" — graph layout used when show = True.

  SEED = None
      None -> each graph is random and not reproducible
      int  -> fix the seed (e.g. 42) for a reproducible corpus.
              Each generation uses SEED + loop_index.

  loop_nb = 296
      Number of graphs to generate in a row.

  generate = 1
      Which graph type to generate (see GENERATORS below):
          1  random       6  regular
          2  bipartite    7  cycle
          3  complete     8  wheel
          4  multipartite 9  grid
          5  tree        10  hypercube
                         11  mycielski

  PARAMS = { ... }
      Parameters for each graph type. Examples:
          "random"       -> {"n": 60, "p": 0.05}      (p = edge probability;
                           you can also use "m" for an exact number of edges)
          "bipartite"    -> {"u": 5, "v": 5, "p": 0.5}
          "complete"     -> {"n": 8}
          "multipartite" -> {"group_sizes": [2, 2, 2]}
          "tree"         -> {"n": 16}
          "regular"      -> {"n": 10, "d": 3}
          "cycle"        -> {"n": 10}
          "wheel"        -> {"n": 10}
          "grid"         -> {"rows": 3, "cols": 4}
          "hypercube"    -> {"d": 3}
          "mycielski"    -> {"k": 4}

--------------------------------------------------------------------------------
3. ADDING / REMOVING ALGORITHMS
--------------------------------------------------------------------------------

Two places must be edited together.

  3.a) The import block (same section as the other algorithm imports)

       from greedy import greedy_coloring
       from backtrack import backtrack_coloring
       from dsatur import dsatur_coloring
       from welsh_powell import welsh_powell_coloring
       from smallest_degree_last import smallest_degree_last_coloring
       from random_greedy import best_random_greedy_coloring
       from rlf import rlf_coloring
       from ido import ido_coloring
       from tabu import tabucol_coloring
       from sa import sa_coloring
       from hea import hea_coloring

       Add:      from my_algo import my_coloring
       Remove:   delete the corresponding import line.

  3.b) The ALGORITHMS list

       ALGORITHMS = [
           ("greedy",               "Greedy",               lambda g: greedy_coloring(g)),
           ("welsh_powell",         "Welsh-Powell",         lambda g: welsh_powell_coloring(g)),
           ("dsatur",               "DSATUR",               lambda g: dsatur_coloring(g)),
           ("ido",                  "IDO",                  lambda g: ido_coloring(g)),
           ("rlf",                  "RLF",                  lambda g: rlf_coloring(g)),
           ("smallest_degree_last", "Smallest-degree-last", lambda g: smallest_degree_last_coloring(g)),
           ("random_greedy",        "Random greedy (x10)",  lambda g: best_random_greedy_coloring(g, trials=10)),
           ("sa",                   "Simulated Annealing",  lambda g: sa_coloring(g, max_iter=20000)),
           ("hea",                  "Hybrid Evolutionary",  lambda g: hea_coloring(g, pop_size=10, max_generations=50, ls_iter=1000)),
           ("tabu",                 "Tabucol",              lambda g: tabucol_coloring(g, max_iter=1000)),
           # ("backtracking", "Backtracking (exact)", lambda g: backtrack_coloring(g)),
       ]

       Each entry is: (machine_id, display_name, callable).

       - machine_id  : short lowercase key stored in the JSON "algorithm"
                       field (e.g. "greedy", "sa", "tabu").
       - display_name: name shown in the terminal report (e.g. "DSATUR").
       - callable    : a function that takes the adjacency matrix and
                       returns (colors, nb_colors).

       Add a new algorithm:
           ("my_algo", "My Algorithm", lambda g: my_coloring(g))

       Remove an algorithm:
           delete (or comment) its line.

  Important notes:

  1. Parameters (max_iter, trials, ...) are given inside the lambda.
     Adjust them to your needs.

  2. The "backtracking" entry is currently commented out because it is an
     exact algorithm and can be extremely slow on large or dense graphs.

  3. Chi (ground truth) logic:
       - if "backtracking" is in the results, chi = backtracking result
         (source = "backtracking");
       - otherwise chi = best heuristic result (source = "best_heuristic").

  4. If you add an algorithm, update the display/JSON names accordingly in
     the analysis scripts too (e.g. results/json/random/html_stats.py and
     json_stats.py), otherwise they will not know about it.

--------------------------------------------------------------------------------
4. GROUND TRUTH AND LABELS
--------------------------------------------------------------------------------

  ground_truth : { "chi": <chromatic number>, "source": "backtracking" or
                   "best_heuristic" }

  labels       : {
      "best_algorithm"      : algorithm with fewest colors (then lowest time),
      "best_n_colors"       : that number of colors,
      "optimal_algorithms"  : list of algorithms that reached chi,
      "n_optimal_algorithms": how many
  }

--------------------------------------------------------------------------------
5. RESULTS FOLDER
--------------------------------------------------------------------------------

  results/json/<graph_type>/  contains the exported JSON files.

  The subfolder results/json/random/ also contains helper scripts documented
  in its own readme.txt (compare.py, html_stats.py, json_stats.py,
  full_report.py).

================================================================================