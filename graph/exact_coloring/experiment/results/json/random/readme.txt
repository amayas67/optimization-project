================================================================================
 README — Random Graph Coloring Results
================================================================================

This folder contains the experimental results for random graphs, together
with a few small helper scripts. This is the same folder where the main
experiment script (graph/exact_coloring/experiment/main.py) writes its JSON
files. Everything here is meant to be simple and easy to adapt. Below is a
short description of each file and how to tweak it when you need to.

--------------------------------------------------------------------------------
1. DATA FOLDERS
--------------------------------------------------------------------------------

  30_vertices/  ,  40_vertices/  ,  50_vertices/  ,  60_vertices/

  Each folder holds the JSON result files for random graphs of that size.
  One JSON file = one graph instance, in the "machine-ready" format:

      schema_version   format version
      run_id           file number (e.g. 000001)
      generated_at     timestamp of the last run
      seed             random seed used to build the graph (null = random)
      instance         graph type, generation parameters, n_vertices,
                       n_edges, and the full adjacency_matrix
      features         structural features (density, degrees, girth, ...)
      ground_truth     chi (chromatic number) and its source
                       ("backtracking" or "best_heuristic")
      results          one entry per algorithm: n_colors, gap_to_chi,
                       optimal, time_ms, solution (color of each vertex)
      labels           best_algorithm, best_n_colors, optimal_algorithms,
                       n_optimal_algorithms

  These JSON files are the input for the scripts below.

--------------------------------------------------------------------------------
2. compare.py — RE-RUN ALL ALGORITHMS ON THE JSON FILES
--------------------------------------------------------------------------------

  Role
  ----
  Reads every JSON file in a target folder, extracts the adjacency matrix,
  runs the coloring algorithms on it, and overwrites the JSON files with
  fresh results (n_colors, time, optimality, labels, ...). At the end of
  each file it is moved into an "<n>_vertices" subfolder, where <n> is the
  number of vertices of the graph, so that full_report.py can aggregate the
  per-size reports afterwards.

  How to use
  ----------
      python3 compare.py

  How to modify
  -------------
  At the top of the file there is a CONFIGURATION section:

      JSON_DIR = ""
          Folder containing the JSON files to process.
          ""            -> use the folder where compare.py lives
          "some/path"   -> relative path (relative to compare.py)
          "/abs/path"   -> absolute path

      ALGO_DIR = ""
          Folder containing the coloring algorithms (algo/*.py).
          ""            -> automatic detection (searches this folder and its
                           parents for graph/exact_coloring/algo)
          "some/path"   -> relative path
          "/abs/path"   -> absolute path

  To include or exclude an algorithm, comment / uncomment its line in the
  ALGORITHMS list:

      ALGORITHMS = [
          ("greedy", "Greedy", lambda g: greedy_coloring(g)),
          # ("backtracking", "Backtracking (exact)", lambda g: backtrack_coloring(g)),
      ]

  A commented line is simply skipped. If "backtracking" is disabled, the
  ground_truth falls back to the best heuristic result
  (source = "best_heuristic").

  Note: backtracking is an exact algorithm and can be very slow on large or
  dense graphs. Disable it if you only need the heuristics.

--------------------------------------------------------------------------------
3. html_stats.py — INTERACTIVE HTML REPORT
--------------------------------------------------------------------------------

  Role
  ----
  Scans the JSON files in the folder where the script is placed and produces
  an interactive page "stats.html":
    - how often each algorithm reached the optimal chi (with percentages),
    - the list of files where each algorithm was optimal / best / not optimal,
    - click on a file to draw the colored graph for every algorithm
      (the drawing is done from the JSON data only, no extra library needed).

  How to use
  ----------
      python3 html_stats.py
      # then open stats.html in a browser

  How to modify
  -------------
  At the top of the file:
      ALGORITHMS          display order and (display name, JSON name) pairs.
      FIRST_TEN_ALGOS     the 10 heuristic algorithms used for the
                          "first ten" group. If you add a new algorithm to
                          ALGORITHMS, add it here too if you want it counted.
      DENSITY_CATEGORIES  density ranges used for the density breakdown.
      SIZE_CATEGORIES     vertex-count ranges used for the size breakdown.

  The script only reads the JSON files in its own folder (non-recursive).

  Exporting files (copy scripts)
  ------------------------------
  In the generated stats.html page, the "union" panel has export buttons
  that produce a copy script for the selected optimal / non-optimal files:
      - copy_optimal_union.sh      (Linux / macOS, bash)
      - copy_non_optimal_union.sh  (Linux / macOS, bash)
      - copy_optimal_union.bat     (Windows)
      - copy_non_optimal_union.bat (Windows)

  Each generated script contains a SOURCE_DIR variable (the folder where the
  JSON files live) and copies the selected files into the CURRENT directory
  (the folder where you run the script). You can freely edit the generated
  .sh / .bat file before running it:
      - change SOURCE_DIR to point to another source folder,
      - run the script from (or cd into) the destination folder you want,
      - or edit the copy commands directly to change the destination.

  Example (bash):
      SOURCE_DIR="/home/amayas/Downloads/projet/optimization-project/graph/exact_coloring/experiment/results/json/random/60_vertices"
      for id in 000001 000002 000003; do
          cp "$SOURCE_DIR/$id.json" .
      done

  Example (Windows .bat):
      set "SOURCE_DIR=C:\path\to\json\folder"
      copy "%SOURCE_DIR%\000001.json" .
      copy "%SOURCE_DIR%\000002.json" .

--------------------------------------------------------------------------------
4. json_stats.py — TEXT STATISTICS REPORT

  Role
  ----
  Scans the JSON files in the folder where the script is placed and writes a
  plain-text report "json_stats_results.txt". For each algorithm it lists the
  files where it was optimal and the files where it was not, with percentages.
  It also adds a "The first ten" group (the 10 heuristics together).

  How to use
  ----------
      python3 json_stats.py
      # results are printed to the console and saved to json_stats_results.txt

  How to modify
  -------------
  At the top of the file:
      self.algorithms     display names of the algorithms.
      self.algo_name_map  mapping from display name to the JSON "algorithm"
                          key. If you rename an algorithm in compare.py,
                          update this mapping accordingly.

--------------------------------------------------------------------------------
5. full_report.py — AGGREGATE THE HTML REPORTS
--------------------------------------------------------------------------------

  Role
  ----
  Meant to be placed in a folder that contains several subfolders (e.g.
  30_vertices, 40_vertices, 50_vertices, 60_vertices). For each subfolder
  that contains a "stats.html", it copies that file into a "full_report"
  folder, prefixed with the vertex count found in the subfolder name:

      50_vertices/stats.html  ->  full_report/50_stats.html

  How to use
  ----------
      python3 full_report.py

  How to modify
  -------------
  The prefix is extracted from the folder name with a simple regex
  (extract_vertex_count). If your folder names do not start with a number,
  the whole folder name is used as the prefix.

--------------------------------------------------------------------------------
6. full_report/ — AGGREGATED REPORTS
--------------------------------------------------------------------------------

  Output folder created by full_report.py. Contains one prefixed HTML report
  per vertex-count subfolder (e.g. 30_stats.html, 40_stats.html, ...).

--------------------------------------------------------------------------------
7. TYPICAL WORKFLOW
--------------------------------------------------------------------------------

  0. (Optional) Generate fresh JSON files with the main experiment:
         python3 ../experiment/main.py      (writes JSON files into this folder)

  1. Re-run / refresh the algorithm results and group the files by size:
         python3 compare.py                 (edit JSON_DIR / ALGO_DIR / ALGORITHMS first)
         After this step, every JSON file lives in its "<n>_vertices" folder,
         where <n> is the number of vertices of the graph.

  2. Inside EACH vertex folder (30_vertices/, 40_vertices/, ...), produce the
     interactive HTML report and the plain-text statistics:
         cp ../html_stats.py 30_vertices/
         cp ../json_stats.py 30_vertices/
         cd 30_vertices && python3 html_stats.py && python3 json_stats.py
         (repeat for every size folder)

  3. Aggregate the per-size reports:
         python3 full_report.py             (run in this folder, random/)
         -> fills full_report/ with one prefixed HTML file per size.

================================================================================