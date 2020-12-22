import asyncio
import logging
import os

from . import Daemon


logging.basicConfig(level=logging.INFO)

socket_path = os.path.join(os.environ["XDG_RUNTIME_DIR"], 'playerctlctl')
asyncio.run(Daemon(socket_path).run())