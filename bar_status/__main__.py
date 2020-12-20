import asyncio
import logging

from xdg import xdg_runtime_dir
from . import Status

logging.basicConfig(level=logging.WARN)

socket_path = str(xdg_runtime_dir() / 'playerctlctl')
asyncio.run(Status(socket_path).run())