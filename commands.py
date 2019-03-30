from gi.repository import Playerctl

STR_TO_LOOP_STATUS = {
    e.value_nick.lower(): e
    for e in Playerctl.LoopStatus.__enum_values__.values()
}

class Commands:
    def __init__(self, move_current_player_index):
        self.move_current_player_index = move_current_player_index

    def volume(self, player, level=None, absolute=True):
        if level is not None:
            if absolute:
                player.set_volume(level)
            else:
                player.set_volume(player.props.volume + level)
        return player.props.volume

    def status(self, player):
        return player.get_property('playback-status').value_nick

    def metadata(self, player, key):
        return player.print_metadata_prop(key) or ''

    def loop(self, player, status=None):
        if status:
            status = STR_TO_LOOP_STATUS.get(status.lower(), None)
            if status is None:
                return ('Error: Invalid status, expected one of the following: '
                    f'{", ".join(STR_TO_LOOP_STATUS.keys())}')
            player.set_loop_status(status)
        return player.get_property('loop-status').value_nick

    def shuffle(self, player, status=None):
        if status:
            player.set_shuffle(status)
        return player.props.shuffle

    def next_player(self, player):
        self.move_current_player_index(1)

    def previous_player(self, player):
        self.move_current_player_index(-1)

    def player_name(self, player):
        return player.get_property('player-name')