import asyncio
import logging

from .rpc_wrapper import RPCWrapper
from .outputter import print_output

logger = logging.getLogger('status')


class Status:
    def __init__(self, socket_path, max_output_length=100):
        self.socket_path = socket_path
        self.force_update = None
        self.max_output_length = max_output_length

    async def handle_request(self, rpc, request):
        if request.method != 'event':
            logger.warn(f'Unexpected request: {request.serialize()}')
            return
        # Prevent deadlock by setting event instead of awaiting outputter
        self.force_update.set()

    async def output_loop(self, rpc):
        await rpc.do_request('ctl_subscribe')
        while 1:
            await print_output(rpc)
            await asyncio.wait(
                [asyncio.sleep(0.5), self.force_update.wait()],
                return_when=asyncio.FIRST_COMPLETED
            )
            self.force_update.clear()

    async def main_loop(self, reader, writer):
        rpc = RPCWrapper(reader, writer)
        output_loop = asyncio.create_task(self.output_loop(rpc))
        try:
            await rpc.main_loop(self.handle_request)
        finally:
            output_loop.cancel()

    async def connect(self):
        while 1:
            try:
                return await asyncio.open_unix_connection(self.socket_path)
            except ConnectionRefusedError as e:
                print(f'Failed to connect: {e}')
                await asyncio.sleep(5)

    async def run(self):
        self.force_update = asyncio.Event()
        while 1:
            reader, writer = await self.connect()
            try:
                await self.main_loop(reader, writer)
            except ConnectionError as e:
                print(f'Disconnected: {e}')