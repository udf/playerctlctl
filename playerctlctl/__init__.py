#!/usr/bin/env python3
"""A daemon to make controlling multiple players easier."""

__version__ = '0.1.0'

import os
import socket
import socketserver
import sys
import threading
import traceback
from distutils.util import strtobool

import gi
gi.require_version('Playerctl', '2.0')
from gi.repository import Playerctl, GLib

from .outputter import Outputter
from . import commands
from .commands import Commands

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
    'next_player': (),
    'player_name': (),
    'previous_player': (),
}


class ServerHandler(socketserver.StreamRequestHandler):
    def actually_handle(self, player):
        if not player:
            return 'Error: No players found'

        args = self.rfile.readline().decode('ascii').strip('\0\n').split('\0')
        if not args:
            return 'Error: No data provided'
        command_name, args = args[0], args[1:]
        arg_types = COMMAND_ARGS.get(command_name, None)
        if arg_types is None:
            return 'Error: Unknown function'

        try:
            for i, (arg, arg_type) in enumerate(zip(args, arg_types)):
                args[i] = arg_type(arg)
        except ValueError as e:
            return f'Error: {str(e)}'

        commands = Commands(self.server.main, player)
        f = getattr(commands, command_name, None)
        if not f:
            f = getattr(player, command_name, None)
        if not f:
            return 'Error: Function not found'
 
        try:
            ret = f(*args)
        except Exception as e:
            return f'Error: {type(e).__name__}: {str(e)}'
        if ret is not None:
            return str(ret)
        return 'Success'

    def handle(self):
        output = self.actually_handle(self.server.main.get_current_player())
        self.wfile.write(f'{output}\n'.encode('ascii'))

    @classmethod
    def serve_forever(cls, main):
        with socketserver.UnixStreamServer(main.socket_path, cls) as server:
            server.main = main
            server.serve_forever()


class Main:
    def __init__(self, args, socket_path):
        self.args = args
        self.current_player_index = 0

        output_len = None
        if len(args) > 1:
            output_len = int(args[1])
        self.outputter = Outputter(output_len)

        self.player_manager = Playerctl.PlayerManager()
        self.socket_path = socket_path

    def get_current_player(self):
        players = self.player_manager.props.players
        if not players:
            return
        # Move index backwards until it's 0 or a valid index
        while self.current_player_index > 0 and self.current_player_index >= len(players):
            self.current_player_index -= 1
        return players[self.current_player_index]

    def move_current_player_index(self, amount):
        players = self.player_manager.props.players
        if not players:
            return False
        self.current_player_index = (self.current_player_index + amount) % len(players)
        self.update_status()
        return True

    def player_state_change(self, player, *args):
        current_player = self.get_current_player()
        if player == current_player:
            self.update_status()

    def update_status(self):
        try:
            self.outputter.on_status_change(self.get_current_player())
        except Exception as e:
            traceback.print_exc()
        return True

    def player_init(self, name):
        player = Playerctl.Player.new_from_name(name)
        for signal_name in PLAYER_SIGNALS:
            player.connect(signal_name, self.player_state_change, signal_name)
        self.player_manager.manage_player(player)

    def on_name_appeared(self, manager, name):
        self.player_init(name)

    def run(self):
        check_socket(self.socket_path)

        self.player_manager.connect('name-appeared', self.on_name_appeared)
        for name in self.player_manager.props.player_names:
            self.player_init(name)

        threading.Thread(target=ServerHandler.serve_forever,
                args=(self,)).start()
        GLib.timeout_add(500, self.update_status)
        GLib.MainLoop().run()


def check_socket(socket_path):
    # Try to connect to a previous instance's socket
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.connect(socket_path)
    except ConnectionRefusedError:
        os.remove(socket_path)
    except FileNotFoundError:
        pass
    else:
        raise RuntimeError('An instance of playerctlctl seems to already be '
                'running for this user')