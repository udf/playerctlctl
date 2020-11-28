import sys
from gi.repository import Playerctl, GLib

# These icons are from nerd-fonts
# https://github.com/ryanoasis/nerd-fonts
STATUS_ICONS = {
    Playerctl.PlaybackStatus.PAUSED: '',
    Playerctl.PlaybackStatus.PLAYING: '',
    Playerctl.PlaybackStatus.STOPPED: ''
}

def ljust_clip(string, n):
    if len(string) > n:
        return string[:n-3] + '...'
    return string.ljust(n)


def get_position_info(position, metadata):
    def fmt(microseconds):
        if microseconds is None:
            return '--:--'
        hours, rem = divmod(round(microseconds / 10**6), 3600)
        minutes, seconds = divmod(rem, 60)
        if hours:
            return f'{hours:02}:{minutes:02}:{seconds:02}'
        return f'{minutes:02}:{seconds:02}'

    position_str = fmt(position)
    duration = metadata.get('mpris:length', 0)

    if duration:
        return f'{position_str}/{fmt(duration)}', position / duration

    return f'{position_str}', 0


def get_trackname(metadata):
    title = metadata.get('xesam:title', '')
    artist = metadata.get('xesam:artist', '')

    if not artist:
        return title
    if isinstance(artist, list):
        artist = ', '.join(artist)

    return f'{artist} - {title}'


class Outputter:
    def __init__(self, output_len=100):
        self.output_len = output_len
        self.previous_output = ''
        self.previous_volume = 0
        self.show_volume_steps = 20

    def get_output(self, player):
        if not player:
            return ' ' * self.output_len

        output = ''
        metadata = player.props.metadata.unpack()
        try:
            position = player.get_position()
        except GLib.GError:
            position = None
        position_str, percent = get_position_info(position, metadata)

        # Status icon
        output += STATUS_ICONS.get(player.get_property('playback-status'))
        output += ' '

        # Player name
        output += f"[{player.get_property('player-name')}]"

        # Position
        output += f'[{position_str}]'

        # Volume
        volume = round(player.props.volume * 100)
        if volume != self.previous_volume:
            self.show_volume_steps = 10
            self.previous_volume = volume
        self.show_volume_steps = max(0, self.show_volume_steps - 1)
        if self.show_volume_steps > 0:
            output += f'[ {volume}%]'

        # Track name
        output += ' ' + get_trackname(metadata)

        # Left-justify/clip output
        output = ljust_clip(output, self.output_len)

        # Add underline tags to show player position
        end_underline_i = round(percent * self.output_len)
        output = '%{u#fff}' + output[:end_underline_i] + '%{-u}' + output[end_underline_i:]

        return output

    def on_status_change(self, player):
        output = self.get_output(player)
        if output != self.previous_output:
            print(output, flush=True)
            self.previous_output = output
