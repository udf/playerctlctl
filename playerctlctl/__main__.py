import sys
import os
from xdg import xdg_runtime_dir
from . import Main

kwargs = {}
if len(sys.argv) > 1:
    kwargs['output_len'] = int(sys.argv[1])
Main(**kwargs).run(xdg_runtime_dir() / 'playerctlctl')