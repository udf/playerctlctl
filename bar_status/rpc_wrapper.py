import asyncio
import logging
import traceback

from tinyrpc.protocols.jsonrpc import JSONRPCProtocol
from tinyrpc import RPCError, InvalidReplyError


rpc = JSONRPCProtocol()
logger = logging.getLogger('rpc')


async def dummy_req_handler(rpc, request):
    pass


class RPCWrapper:
    def __init__(self, reader, writer):
        self.reader = reader
        self.writer = writer
        self.pending_requests = {}
        self.callbacks_queue = asyncio.Queue()

    async def do_request(self, method, args=None, kwargs=None, one_way=False):
        req = rpc.create_request(method, args=args, kwargs=kwargs, one_way=one_way)

        logger.debug(f'Sending msg #{req.unique_id}: {req.serialize()}')
        self.writer.write(req.serialize())
        self.writer.write(b'\n')
        await self.writer.drain()

        # Put future in dict so we can set the result when the response comes back
        fut = asyncio.Future()
        self.pending_requests[req.unique_id] = fut

        ret = await asyncio.wait_for(fut, 5)
        if hasattr(ret, 'error'):
            raise RPCError(ret.error)
        return ret.result

    async def callbacks_loop(self):
        while 1:
            coro = await self.callbacks_queue.get()
            try:
                await coro
            except Exception as e:
                logger.warn(f'Unexpected exception in rpc request loop: {e}')
                logger.warn(traceback.format_exc())

    async def main_loop_inner(self, request_handler):
        try:
            msg = await self.reader.readline()
            if not msg:
                return True
            try:
                reply = rpc.parse_reply(msg)
            except InvalidReplyError:
                request = rpc.parse_request(msg)
                self.callbacks_queue.put_nowait(request_handler(self, request))
                return
            fut = self.pending_requests.get(reply.unique_id, None)
            if not fut:
                logger.warn(f'Unexpected reply: {msg}')
                return
            logger.debug(f'Got reply to #{reply.unique_id}: {msg}')
            fut.set_result(reply)
            del self.pending_requests[reply.unique_id]
        except Exception as e:
            logger.warn(f'Unexpected exception in rpc loop: {e}')
            logger.warn(traceback.format_exc())
            if isinstance(e, ConnectionError):
                return True

    async def main_loop(self, request_handler=dummy_req_handler):
        callbacks_loop = asyncio.create_task(self.callbacks_loop())
        try:
            while 1:
                should_break = await self.main_loop_inner(request_handler)
                if should_break:
                    break
        finally:
            callbacks_loop.cancel()