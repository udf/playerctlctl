import inspect
from gi.repository import Playerctl


def get_player_instance(player):
    if not player:
        return ''
    return player.get_property('player-instance')


def is_player_active(player):
    return player.get_property('playback-status') == Playerctl.PlaybackStatus.PLAYING


def are_params_valid(method, args, kwargs):
    if hasattr(method, '__code__'):
        try:
            inspect.getcallargs(method, *args, **kwargs)
        except TypeError:
            return False
    return True