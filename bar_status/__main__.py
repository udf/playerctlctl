import asyncio
import logging
import os
import sys

from . import Status

logging.basicConfig(level=logging.WARN)

max_length = 100
if len(sys.argv) > 1:
    max_length = int(sys.argv[1])

socket_path = os.path.join(os.environ["XDG_RUNTIME_DIR"], 'playerctlctl')
asyncio.run(Status(socket_path, max_length).run())