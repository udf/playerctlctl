"""A daemon to make controlling multiple players easier."""

__version__ = '0.2.0'

import os
import asyncio
import concurrent.futures
import logging
from functools import partial
from distutils.util import strtobool

import gi
gi.require_version('Playerctl', '2.0')
from gi.repository import Playerctl, GLib
from tinyrpc.protocols.jsonrpc import JSONRPCProtocol
from tinyrpc import MethodNotFoundError, BadRequestError, InvalidParamsError

from .utils import get_player_instance, is_player_active, are_params_valid
from .commands import Commands


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('daemon')
rpc = JSONRPCProtocol()

PLAYER_SIGNALS = (
    'loop-status', 'metadata', 'seeked', 'shuffle', 'volume'
)


class Daemon:
    def __init__(self, socket_path):
        self.current_player_index = 0
        self.current_player = None
        self.signal_handlers = []
        self.socket_path = socket_path
        self.player_manager = Playerctl.PlayerManager()
        self.event_loop = None
        self.event_listeners = set()

    def init_glib(self):
        self.player_manager.connect('name-appeared', self.on_name_appeared)
        self.player_manager.connect('player-appeared', self.on_player_appeared)
        self.player_manager.connect('player-vanished', self.on_player_vanished)

        for name in self.player_manager.props.player_names:
            self.player_init(name)

        return False

    def player_init(self, name):
        player = Playerctl.Player.new_from_name(name)
        player.connect('playback-status', self.on_playback_state_change)
        self.player_manager.manage_player(player)

    def set_current_player(self, player):
        def inner():
            if player is None:
                logger.debug('Unsetting current player')
                self.current_player_index = 0
                self.current_player = None
                return
            players = self.player_manager.props.players
            self.current_player_index = players.index(player)
            self.current_player = player
            logger.debug(f'Current player set to [{self.current_player_index}] = {get_player_instance(self.current_player)}')

        prev_player = self.current_player
        inner()
        if self.current_player != prev_player:
            if prev_player:
                for handler_id in self.signal_handlers:
                    prev_player.disconnect(handler_id)
                self.signal_handlers = []
  
            for signal_name in PLAYER_SIGNALS:
                handler_id = self.current_player.connect(
                    signal_name,
                    partial(self.on_player_signal, signal_name)
                )
                self.signal_handlers.append(handler_id)

            self.publish_event(
                'ctl_player_change',
                instance=get_player_instance(self.current_player)
            )

    def move_current_player_index(self, amount):
        players = self.player_manager.props.players
        if not players:
            return None
        new_index = (self.current_player_index + amount) % len(players)
        self.set_current_player(players[new_index])
        return get_player_instance(self.current_player)

    def find_first_active_player(self):
        return next(
            (
                player
                for player in self.player_manager.props.players
                if is_player_active(player)
            ),
            None
        )

    def on_player_signal(self, event, player, *args):
        args = list(args)
        for i, v in enumerate(args):
            if hasattr(v, 'unpack'):
                args[i] = v.unpack()
        self.publish_event(event, data=args)

    def on_playback_state_change(self, player, state):
        if player == self.current_player:
            self.publish_event('playback-status', data=[state.value_nick])
        if is_player_active(self.current_player):
            return
        if state == Playerctl.PlaybackStatus.PLAYING:
            self.set_current_player(player)
            return
        active_player = self.find_first_active_player()
        if player == self.current_player and active_player:
            self.set_current_player(active_player)

    def on_name_appeared(self, manager, name):
        self.player_init(name)

    def on_player_appeared(self, manager, player):
        logger.debug(f'Player added: {get_player_instance(player)}')
        players = self.player_manager.props.players

        active_player = self.find_first_active_player()
        if self.current_player is None:
            self.set_current_player(active_player or players[0])
            return
        if not is_player_active(self.current_player) and active_player:
            self.set_current_player(active_player)
            return
        self.set_current_player(self.current_player)

    def on_player_vanished(self, manager, player):
        logger.debug(f'Player vanished: {get_player_instance(player)}')
        players = self.player_manager.props.players

        if player != self.current_player:
            self.set_current_player(self.current_player)
            return

        logger.debug('Current player has vanished')
        if not players:
            self.set_current_player(None)
            return
        next_player = players[min(self.current_player_index, len(players) - 1)]
        self.set_current_player(self.find_first_active_player() or next_player)

    def publish_event(self, event, **kwargs):
        logger.debug(f'Publishing event: {event}={kwargs}')
        stale_listeners = set()
        for listener in self.event_listeners:
            ret = asyncio.run_coroutine_threadsafe(
                listener(event, **kwargs),
                self.event_loop
            ).result()
            if not ret:
                stale_listeners.add(listener)
        self.event_listeners = self.event_listeners - stale_listeners
        if stale_listeners:
            logger.debug(f'Removed {len(stale_listeners)} stale listener(s)')

    def handle_socket_req(self, req, send_event):
        s = req.method.split('.', 1)
        if len(s) == 2:
            namespace, method = s
        else:
            namespace, method = None, req.method

        obj = {
            'player': self.current_player
        }.get(namespace, Commands(self, send_event))

        f = getattr(obj, method, None)
        if not f:
            return req.error_respond(MethodNotFoundError())

        if not are_params_valid(f, req.args, req.kwargs):
            return req.error_respond(InvalidParamsError())

        try:
            ret = f(*req.args, **req.kwargs)
        except Exception as e:
            return req.error_respond(e)
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
                res = self.handle_socket_req(req, send_event)
            except BadRequestError as e:
                res = e.error_respond()
            except:
                res = BadRequestError().error_respond()
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
        await self.check_socket()

        pool = concurrent.futures.ThreadPoolExecutor()
        GLib.timeout_add(0, self.init_glib)
        f = self.event_loop.run_in_executor(pool, lambda: GLib.MainLoop().run())

        server = await asyncio.start_unix_server(self.handle_socket, self.socket_path)
        async with server:
            await server.serve_forever()