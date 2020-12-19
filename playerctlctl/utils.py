from gi.repository import Playerctl


def get_player_instance(player):
    if not player:
        return ''
    return player.get_property('player-instance')


def is_player_active(player):
    return player.get_property('playback-status') == Playerctl.PlaybackStatus.PLAYING
