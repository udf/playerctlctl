"""A daemon to make controlling multiple players easier."""

__version__ = '0.2.0'

import os
import asyncio
import concurrent.futures
import logging
from distutils.util import strtobool

import gi
gi.require_version('Playerctl', '2.0')
from gi.repository import Playerctl, GLib

from . import commands
from .commands import Commands


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('daemon')

PLAYER_SIGNALS = (
    'loop-status', 'metadata', 'playback-status', 'seeked',
    'shuffle', 'volume'
)

COMMAND_ARGS = {
    # playerctl commands (ones marked with # are wrapped)
    'loop': (str,), #
    'metadata': (str,), #
    'next': (),
    'open': (str,),
    'pause': (),
    'play': (),
    'play_pause': (),
    'position': (int, strtobool), #
    'previous': (),
    'shuffle': (strtobool,), #
    'status': (), #
    'stop': (),
    'volume': (float, strtobool), #

    # playerctlctl commands
    'ctl_next': (),
    'ctl_previous': (),
    'ctl_instance': (),
}


def get_player_instance(player):
    if not player:
        return ''
    return player.get_property('player-instance')


def is_player_active(player):
    return player.get_property('playback-status') == Playerctl.PlaybackStatus.PLAYING


class Daemon:
    def __init__(self, socket_path):
        self.current_player_index = 0
        self.current_player = None
        self.socket_path = socket_path
        self.player_manager = Playerctl.PlayerManager()

    def set_current_player(self, player):
        if player is None:
            logger.debug('Unsetting current player')
            self.current_player_index = 0
            self.current_player = None
            return
        players = self.player_manager.props.players
        logger.debug(f'Current player was [{self.current_player_index}] = {get_player_instance(self.current_player)}')
        self.current_player_index = players.index(player)
        self.current_player = player
        logger.debug(f'Current player set to [{self.current_player_index}] = {get_player_instance(self.current_player)}')

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

    def player_init(self, name):
        player = Playerctl.Player.new_from_name(name)
        player.connect('playback-status', self.on_playback_state_change)
        self.player_manager.manage_player(player)

    def on_name_appeared(self, manager, name):
        logger.debug(f'New player: {name.instance}')
        self.player_init(name)

    def on_playback_state_change(self, player, state):
        if is_player_active(self.current_player):
            return
        if state == Playerctl.PlaybackStatus.PLAYING:
            self.set_current_player(player)
            return
        active_player = self.find_first_active_player()
        if player == self.current_player and active_player:
            self.set_current_player(active_player)

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

    def handle_socket_oneshot(self, args):
        if not self.current_player:
            return 'Error: No players found'
        if not args:
            return 'Error: No input provided'

        command_name, args = args[0], args[1:]
        arg_types = COMMAND_ARGS.get(command_name, None)
        if arg_types is None:
            return 'Error: Unknown function'

        try:
            for i, (arg, arg_type) in enumerate(zip(args, arg_types)):
                args[i] = arg_type(arg)
        except ValueError as e:
            return f'Error: {str(e)}'

        commands = Commands(self)
        f = getattr(commands, command_name, None)
        if not f:
            f = getattr(self.current_player, command_name, None)
        if not f:
            return 'Error: Function not found'
 
        try:
            ret = f(*args)
        except Exception as e:
            return f'Error: {type(e).__name__}: {str(e)}'
        if ret is not None:
            return str(ret)
        return 'Success'

    async def handle_socket(self, reader, writer):
        args = (await reader.readline()).decode('ascii').strip('\0\n').split('\0')
        output = self.handle_socket_oneshot(args)
        writer.write(f'{output}\n'.encode('ascii'))
        writer.close()
        await writer.wait_closed()

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
        await self.check_socket()
        self.player_manager.connect('name-appeared', self.on_name_appeared)
        self.player_manager.connect('player-appeared', self.on_player_appeared)
        self.player_manager.connect('player-vanished', self.on_player_vanished)

        for name in self.player_manager.props.player_names:
            self.player_init(name)

        loop = asyncio.get_running_loop()
        pool = concurrent.futures.ThreadPoolExecutor()
        f = loop.run_in_executor(pool, lambda: GLib.MainLoop().run())

        server = await asyncio.start_unix_server(self.handle_socket, self.socket_path)
        async with server:
            await server.serve_forever()