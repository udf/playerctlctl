"""
A daemon to make controlling multiple players easier.

Daemon core, contains the glib event loop
"""

import logging
from functools import partial

import gi
gi.require_version('Playerctl', '2.0')
from gi.repository import Playerctl, GLib

from .utils import get_player_instance, is_player_active

logger = logging.getLogger('core')

PLAYER_SIGNALS = (
    'loop-status', 'metadata', 'seeked', 'shuffle', 'volume'
)

class Core:
    def __init__(self, publish_event_callback):
        self.current_player_index = 0
        self.current_player = None
        self.signal_handlers = []
        self.player_manager = None
        self.publish_event_callback = publish_event_callback

    def set_current_player(self, player):
        prev_player = self.current_player

        if player is None:
            logger.debug('Unsetting current player')
            self.current_player_index = 0
            self.current_player = None
        else:
            self.current_player_index = self.player_manager.props.players.index(player)
            self.current_player = player
            logger.debug(f'Current player set to [{self.current_player_index}] = {get_player_instance(self.current_player)}')

        if self.current_player != prev_player:
            # Disconnect old handlers and connect to new player
            if prev_player:
                for handler_id in self.signal_handlers:
                    prev_player.disconnect(handler_id)
                self.signal_handlers = []

            if self.current_player:
                for signal_name in PLAYER_SIGNALS:
                    handler_id = self.current_player.connect(
                        signal_name,
                        partial(self.on_current_player_signal, signal_name)
                    )
                    self.signal_handlers.append(handler_id)

            self.publish_event_callback(
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

    def player_init(self, name):
        player = Playerctl.Player.new_from_name(name)
        player.connect('playback-status', self.on_playback_state_change)
        self.player_manager.manage_player(player)

    def on_current_player_signal(self, event, player, *args):
        # Unpack GVariants so we can send them over RPC
        args = list(args)
        for i, v in enumerate(args):
            if hasattr(v, 'unpack'):
                args[i] = v.unpack()
        self.publish_event_callback(event, data=args)

    def on_playback_state_change(self, player, state):
        if player == self.current_player:
            self.publish_event_callback('playback-status', data=[state.value_nick])
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

        # Switch to new player if it's active
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

    def on_name_appeared(self, manager, name):
        self.player_init(name)

    def run(self):
        self.player_manager = Playerctl.PlayerManager()
        self.player_manager.connect('name-appeared', self.on_name_appeared)
        self.player_manager.connect('player-appeared', self.on_player_appeared)
        self.player_manager.connect('player-vanished', self.on_player_vanished)

        for name in self.player_manager.props.player_names:
            self.player_init(name)

        GLib.MainLoop().run()