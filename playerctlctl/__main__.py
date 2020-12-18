import sys
import os
import asyncio
from xdg import xdg_runtime_dir
from . import Daemon

socket_path = str(xdg_runtime_dir() / 'playerctlctl')
asyncio.run(Daemon(socket_path).run())