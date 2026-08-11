# Package initialiser: expose every solver at the package level so that
# ``import algo; getattr(algo, func_name)`` (used by compare.py's multiprocessing
# worker) can resolve the function by its __name__.
from .greedy import greedy_coloring
from .welsh_powell import welsh_powell_coloring
from .dsatur import dsatur_coloring
from .ido import ido_coloring
from .rlf import rlf_coloring
from .smallest_degree_last import smallest_degree_last_coloring
from .random_greedy import random_greedy_coloring, best_random_greedy_coloring
from .sa import sa_coloring
from .hea import hea_coloring
from .tabu import tabucol_coloring
from .backtrack import backtrack_coloring
from .cpsat import cpsat_coloring
from .sat import sat_coloring
