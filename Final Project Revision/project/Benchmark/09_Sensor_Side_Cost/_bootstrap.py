"""Put Benchmark/_shared on sys.path.

Copied into each experiment folder so `python experiment.py` works from
inside that folder with no PYTHONPATH juggling.
"""
import os
import sys

_here = os.path.dirname(os.path.abspath(__file__))
_shared = os.path.join(os.path.dirname(_here), "_shared")
if os.path.isdir(_shared) and _shared not in sys.path:
    sys.path.insert(0, _shared)
elif _here not in sys.path:
    sys.path.insert(0, _here)
