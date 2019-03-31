from gi.repository import Playerctl

STR_TO_LOOP_STATUS = {
    e.value_nick.lower(): e
    for e in Playerctl.LoopStatus.__enum_values__.values()
}

class Commands:
    def __init__(self, move_current_player_index):
        self.move_current_player_index = move_current_player_index

    def position(self, player, offset=None, absolute=True):
        """
        Sets/Gets the position of the player

        offset -- the time in seconds to set/shift the position by
        absolute -- if true, offset is the exact position
            if false, offset is relative to the current position
        """
        if offset is not None:
            offset *= 1000000
            if absolute:
                player.set_position(offset)
            else:
                player.set_position(player.props.position + offset)
        return player.get_position() / 1000000

    def volume(self, player, level=None, absolute=True):
        """
        Sets/Gets the volume of the player

        volume -- the amount in fractional percent to set/shift the volume by
        absolute -- if true, the volume is set to this number
            if false, the volume is set relative to the current volume
        """
        if level is not None:
            if absolute:
                player.set_volume(level)
            else:
                player.set_volume(player.props.volume + level)
        return player.props.volume

    def status(self, player):
        """
        Gets the status of the player (playing/paused/stopped)

        Returns the value nick name from this enum:
        https://dubstepdish.com/playerctl/PlayerctlPlayer.html#PlayerctlPlaybackStatus
        """
        return player.get_property('playback-status').value_nick

    def metadata(self, player, key):
        """
        Gets a metadata key from the player

        key -- the key to get, docs for possible keys are here:
            https://www.freedesktop.org/wiki/Specifications/mpris-spec/metadata/
        """
        return player.print_metadata_prop(key) or ''

    def loop(self, player, status=None):
        """
        Sets/Gets the loop status of the player

        status -- the nickname of a value from this enum:
            https://dubstepdish.com/playerctl/PlayerctlPlayer.html#PlayerctlLoopStatus
            (ie "none", "track", or "playlist")
        """
        if status:
            status = STR_TO_LOOP_STATUS.get(status.lower(), None)
            if status is None:
                return ('Error: Invalid status, expected one of the following: '
                    f'{", ".join(STR_TO_LOOP_STATUS.keys())}')
            player.set_loop_status(status)
        return player.get_property('loop-status').value_nick

    def shuffle(self, player, status=None):
        """
        Sets/Gets the shuffle status of the player

        status -- boolean
        """
        if status is not None:
            player.set_shuffle(status)
        return player.props.shuffle

    def next_player(self, player):
        """
        Switches the current player to the next controllable player
        """
        self.move_current_player_index(1)

    def previous_player(self, player):
        """
        Switchest the current player to the previous controllable player
        """
        self.move_current_player_index(-1)

    def player_name(self, player):
        """
        Gets the name of the current player
        """
        return player.get_property('player-name')