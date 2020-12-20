from gi.repository import Playerctl

STR_TO_LOOP_STATUS = {
    e.value_nick.lower(): e
    for e in Playerctl.LoopStatus.__enum_values__.values()
}


def require_player(method):
    def wrapper(self, *args, **kwargs):
        if not self.player:
            raise RuntimeError('No active player')
        return method(self, *args, **kwargs)
    return wrapper


class Commands:
    def __init__(self, main, event_cb=None):
        self.main = main
        self.player = main.current_player
        self.event_cb = event_cb

    @require_player
    def get_position(self):
        """
        Gets the position of the player in seconds
        """
        return self.player.get_position() / 1000000

    @require_player
    def set_position(self, offset, absolute=True):
        """
        Sets the position of the player

        offset -- the time in seconds to set/shift the position by
        absolute -- if true, offset is the exact position
            if false, offset is relative to the current position
        """
        offset *= 1000000
        if absolute:
            self.player.set_position(offset)
        else:
           self.player.set_position(self.player.get_position() + offset)
        return self.get_position()

    @require_player
    def get_volume(self):
        """
        Gets the volume of the player
        """
        return self.player.props.volume

    @require_player
    def set_volume(self, level, absolute=True):
        """
        Sets the volume of the player

        volume -- the amount in fractional percent to set/shift the volume by
        absolute -- if true, the volume is set to this number
            if false, the volume is set relative to the current volume
        """
        if absolute:
            self.player.set_volume(level)
        else:
            self.player.set_volume(self.player.props.volume + level)
        return self.get_volume()

    @require_player
    def get_status(self):
        """
        Gets the status of the player (playing/paused/stopped)

        Returns the value nick name from this enum:
        https://dubstepdish.com/playerctl/PlayerctlPlayer.html#PlayerctlPlaybackStatus
        """
        return self.player.get_property('playback-status').value_nick.lower()

    @require_player
    def get_metadata_key(self, key):
        """
        Gets a metadata key from the player

        key -- the key to get, docs for possible keys are here:
            https://www.freedesktop.org/wiki/Specifications/mpris-spec/metadata/
        """
        return self.player.print_metadata_prop(key) or ''

    @require_player
    def get_all_metadata(self):
        """
        Gets all metadata keys from the player
        """
        return self.player.props.metadata.unpack()

    @require_player
    def get_loop_status(self):
        """
        Gets the loop status of the player
        """
        return self.player.get_property('loop-status').value_nick.lower()

    @require_player
    def set_loop_status(self, status):
        """
        Sets/Gets the loop status of the player

        status -- the nickname of a value from this enum:
            https://dubstepdish.com/playerctl/PlayerctlPlayer.html#PlayerctlLoopStatus
            (ie "none", "track", or "playlist")
        """
        status = STR_TO_LOOP_STATUS.get(status.lower(), None)
        if status is None:
            raise RuntimeError(
                'Error: Invalid status, expected one of the following: '
                f'{", ".join(STR_TO_LOOP_STATUS.keys())}'
            )
        self.player.set_loop_status(status)
        return self.get_loop_status()

    @require_player
    def is_shuffled(self):
        """
        Gets the shuffle status of the player
        """
        return self.player.props.shuffle

    @require_player
    def set_shuffled(self, status):
        """
        Sets the shuffle status of the player

        status -- boolean
        """
        self.player.set_shuffle(status)
        return self.is_shuffled()

    def ctl_next(self):
        """
        Switches the current player to the next controllable player
        """
        return self.main.move_current_player_index(1)

    def ctl_previous(self):
        """
        Switchest the current player to the previous controllable player
        """
        return self.main.move_current_player_index(-1)

    def ctl_get_instance(self):
        """
        Gets the instance of the current player
        """
        if not self.player:
            return ''
        return self.player.get_property('player-instance')

    def ctl_get_name(self):
        """
        Gets the name of the current player
        """
        if not self.player:
            return ''
        return self.player.get_property('player-name')

    def ctl_subscribe(self):
        """
        Subscribes to all player events
        """
        self.main.event_listeners.add(self.event_cb)
        return True