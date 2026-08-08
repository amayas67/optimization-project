"""
algo — Graph coloring algorithms package.

Each module exposes a coloring function with the signature::

    coloring_function(adj_matrix, ...) -> (colors, nb_colors)

where ``adj_matrix`` is a symmetric n×n adjacency matrix (list of lists)
with a zero diagonal, ``colors`` is the list of color to color assignments (length n)
and ``nb_colors`` is the number of distinct colors used.
"""

# Core algorithms (always available)
from .dsatur import dsatur_coloring
from .greedy import greedy_coloring
from .ido import ido_coloring
from .random_greedy import best_random_greedy_coloring, random_greedy_coloring
from .rlf import rlf_coloring
from .sa import sa_coloring
from .smallest_degree_last import smallest_degree_last_coloring
from .tabu import tabucol_coloring
from .welsh_powell import welsh_powell_coloring

# Optional algorithms (may require extra dependencies)
try:
    from .backtrack import backtrack_coloring
except ImportError:
    backtrack_coloring = None

try:
    from .cpsat import cpsat_coloring
except ImportError:
    cpsat_coloring = None

try:
    from .hea import hea_coloring
except ImportError:
    hea_coloring = None

try:
    from .sat import sat_coloring
except ImportError:
    sat_coloring = None

__all__ = [
    "dsatur_coloring",
    "greedy_coloring",
    "ido_coloring",
    "best_random_greedy_coloring",
    "random_greedy_coloring",
    "rlf_coloring",
    "sa_coloring",
    "smallest_degree_last_coloring",
    "tabucol_coloring",
    "welsh_powell_coloring",
]

# Add optional algorithms to __all__ if available
if backtrack_coloring is not None:
    __all__.append("backtrack_coloring")

if cpsat_coloring is not None:
    __all__.append("cpsat_coloring")

if hea_coloring is not None:
    __all__.append("hea_coloring")

if sat_coloring is not None:
    __all__.append("sat_coloring")