"""Make the experiment modules importable from the tests.

The experiment scripts live in ``src/experiments`` and import each other by
bare module name (they insert their own directory into ``sys.path`` at run
time). The tests do the same here once, so every test file can simply
``import week06_ground_air_evrp_tw as w6`` and so on.
"""

import os
import sys

_EXPERIMENTS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "src", "experiments")
if _EXPERIMENTS not in sys.path:
    sys.path.insert(0, _EXPERIMENTS)
