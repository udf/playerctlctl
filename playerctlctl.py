#!/usr/bin/python
import os
import socket
import socketserver
import threading
import traceback
from distutils.util import strtobool

import gi
gi.require_version('Playerctl', '2.0')
from gi.repository import Playerctl, GLib

from outputter import on_status_change
import commands
from commands import Commands

PLAYER_SIGNALS = (
    'loop-status', 'metadata', 'playback-status', 'seeked',
    'shuffle', 'volume'
)

COMMAND_ARGS = {
    # playerctl commands (commands marked with # are our own wrappers)
    'play': (),
    'pause': (),
    'play_pause': (),
    'stop': (),
    'next': (),
    'previous': (),
    'position': (int, strtobool), #
    'volume': (float, strtobool), #
    'status': (), #
    'metadata': (str,), #
    'open': (str,),
    'loop': (str,), #
    'shuffle': (strtobool,), #

    # playerctlctl commands
    'next_player': (),
    'previous_player': (),
    'player_name': (),
}

SOCKET_PATH = f'/tmp/playerctlctl{os.getuid()}'


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

        commands = Commands(move_current_player_index, player)
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
        output = self.actually_handle(get_current_player())
        self.wfile.write(f'{output}\n'.encode('ascii'))


def server_main():
    with socketserver.UnixStreamServer(SOCKET_PATH, ServerHandler) as server:
        server.serve_forever()


def get_current_player():
    global current_player_index
    players = player_manager.props.players
    if not players:
        return
    # Move index backwards until it's 0 or a valid index
    while current_player_index > 0 and current_player_index >= len(players):
        current_player_index -= 1
    return players[current_player_index]


def move_current_player_index(amount):
    global current_player_index
    players = player_manager.props.players
    if not players:
        return False
    current_player_index = (current_player_index + amount) % len(players)
    update_status()
    return True


def player_state_change(player, *args):
    current_player = get_current_player()
    if player == current_player:
        update_status()


def update_status():
    try:
        on_status_change(get_current_player())
    except Exception as e:
        traceback.print_exc()
    return True


def player_init(name):
    player = Playerctl.Player.new_from_name(name)
    for signal_name in PLAYER_SIGNALS:
        player.connect(signal_name, player_state_change, signal_name)
    player_manager.manage_player(player)


def on_name_appeared(manager, name):
    player_init(name)


def check_socket():
    # Try to connect to a previous instance's socket
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.connect(SOCKET_PATH)
    except ConnectionRefusedError as e:
        os.remove(SOCKET_PATH)
    except FileNotFoundError:
        pass
    else:
        raise RuntimeError('An instance of playerctlctl seems to already be running for this user')


check_socket()
current_player_index = 0

player_manager = Playerctl.PlayerManager()
player_manager.connect('name-appeared', on_name_appeared)
for name in player_manager.props.player_names:
    player_init(name)

threading.Thread(target=server_main).start()
GLib.timeout_add(500, update_status)
GLib.MainLoop().run()
