"""
A daemon to make controlling multiple players easier.

Contains the RPC server, runs the core code (core.py) in a separate thread.
"""

__version__ = '0.2.0'

import os
import asyncio
import inspect
import concurrent.futures
import logging

from tinyrpc.protocols.jsonrpc import JSONRPCProtocol
from tinyrpc import MethodNotFoundError, BadRequestError, InvalidParamsError

from .core import Core
from .utils import on_exception, are_params_valid
from .commands import Commands


logger = logging.getLogger('daemon')
rpc = JSONRPCProtocol()


class Daemon:
    def __init__(self, socket_path):
        self.socket_path = socket_path
        self.event_loop = None
        self.core = None
        self.event_queue = None
        self.event_listeners = set()

    def publish_event(self, event, **kwargs):
        self.event_loop.call_soon_threadsafe(
            lambda: self.event_queue.put_nowait((event, kwargs))
        )

    async def event_publisher_loop(self):
        while 1:
            event, kwargs = await self.event_queue.get()
            logger.debug(f'Publishing event: {event}={kwargs}')

            listener_statuses = await asyncio.gather(
                *(listener(event, **kwargs) for listener in self.event_listeners)
            )

            stale_listeners = {
                listener
                for listener, is_valid in zip(self.event_listeners, listener_statuses)
                if not is_valid
            }

            self.event_listeners = self.event_listeners - stale_listeners
            if stale_listeners:
                logger.debug(f'Removed {len(stale_listeners)} stale listener(s)')

    @on_exception(lambda e, self, req, send_event: req.error_respond(e))
    def handle_socket_req(self, req, send_event):
        s = req.method.split('.', 1)
        if len(s) == 2:
            namespace, method = s
        else:
            namespace, method = '', req.method

        # Commands will be run on the current (asyncio) thread,
        # this is not correct, but it will work since
        # we do not block anywhere in the Core class or the publish event method
        obj = {
            'player': self.core.current_player,
            '': Commands(self, send_event)
        }.get(namespace, None)

        f = getattr(obj, method, None)
        if not f:
            return req.error_respond(MethodNotFoundError())

        if not are_params_valid(f, req.args, req.kwargs):
            return req.error_respond(InvalidParamsError())

        ret = f(*req.args, **req.kwargs)
        return req.respond(ret)

    async def run_rpc_loop(self, reader, writer):
        async def send_event(event, **kwargs):
            kwargs = {**kwargs, **{'event': event}}
            notification = rpc.create_request(f'event', kwargs=kwargs, one_way=True)
            try:
                writer.write(notification.serialize())
                writer.write(b'\n')
                await writer.drain()
            except (ConnectionAbortedError, ConnectionResetError):
                return False
            return True

        while 1:
            msg = await reader.readline()
            if not msg:
                break
            try:
                req = rpc.parse_request(msg)
            except BadRequestError as e:
                res = e.error_respond()
            else:
                res = self.handle_socket_req(req, send_event)
            writer.write(res.serialize())
            writer.write(b'\n')
            await writer.drain()

    async def handle_socket(self, reader, writer):
        try:
            await self.run_rpc_loop(reader, writer)
        except (ConnectionAbortedError, ConnectionResetError):
            pass

    async def check_socket(self):
        try:
            reader, writer = await asyncio.open_unix_connection(self.socket_path)
        except ConnectionRefusedError:
            os.remove(self.socket_path)
        except FileNotFoundError:
            pass
        else:
            raise RuntimeError(
                'An instance of playerctlctl seems to already be running for this user'
            )

    async def run(self):
        self.event_loop = asyncio.get_running_loop()
        self.event_queue = asyncio.Queue()
        await self.check_socket()

        self.core = Core(self.publish_event)
        pool = concurrent.futures.ThreadPoolExecutor()
        self.event_loop.run_in_executor(pool, self.core.run)

        event_publisher = asyncio.create_task(self.event_publisher_loop())
        server = await asyncio.start_unix_server(self.handle_socket, self.socket_path)
        try:
            async with server:
                await server.serve_forever()
        finally:
            event_publisher.cancel()