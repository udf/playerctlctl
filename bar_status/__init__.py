import asyncio
import logging
import traceback

from .rpc_wrapper import RPCWrapper
from .outputter import print_output

logger = logging.getLogger('status')


class Status:
    def __init__(self, socket_path, max_output_length=100):
        self.socket_path = socket_path
        self.max_output_length = max_output_length

    async def handle_request(self, rpc, request):
        if request.method != 'event':
            logger.warn(f'Unexpected request: {request.serialize()}')
            return
        await print_output(rpc, self.max_output_length)

    async def output_loop(self, rpc):
        await rpc.do_request('ctl_subscribe')
        while 1:
            try:
                await print_output(rpc, self.max_output_length)
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.warn(f'Unexpected exception in output loop: {e}')
                logger.warn(traceback.format_exc())

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
        while 1:
            reader, writer = await self.connect()
            try:
                await self.main_loop(reader, writer)
            except ConnectionError as e:
                print(f'Disconnected: {e}')