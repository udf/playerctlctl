import sys
import os
from . import Main

kwargs = {}
if len(sys.argv) > 1:
    kwargs['output_len'] = int(sys.argv[1])
Main(**kwargs).run(f'/tmp/playerctlctl{os.getuid()}')