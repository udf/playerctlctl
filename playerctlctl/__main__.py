import sys
import os
from . import Main

Main(sys.argv, f'/tmp/playerctlctl{os.getuid()}').run()