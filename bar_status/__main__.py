import asyncio
import sys
import logging

from xdg import xdg_runtime_dir
from . import Status

logging.basicConfig(level=logging.WARN)

max_length = 100
if len(sys.argv) > 1:
    max_length = int(sys.argv[1])

socket_path = str(xdg_runtime_dir() / 'playerctlctl')
asyncio.run(Status(socket_path, max_length).run())