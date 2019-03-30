import sys
from gi.repository import Playerctl

STATUS_ICONS = {
    Playerctl.PlaybackStatus.PAUSED: '',
    Playerctl.PlaybackStatus.PLAYING: '',
    Playerctl.PlaybackStatus.STOPPED: ''
}

previous_output = ''
output_len = int(sys.argv[1]) if len(sys.argv) > 1 else 100


def ljust_clip(string, n):
    if len(string) > n:
        return string[:n-3] + '...'
    return string.ljust(n)


def get_position_info(position, metadata):
    def fmt(microseconds):
        hours, rem = divmod(round(microseconds / 10**6), 3600)
        minutes, seconds = divmod(rem, 60)
        if hours:
            return f'{hours:02}:{minutes:02}:{seconds:02}'
        return f'{minutes:02}:{seconds:02}'

    position_str = fmt(position)
    duration = metadata.get('mpris:length', 0)

    if duration:
        return '{}/{}'.format(position_str, fmt(duration)), position / duration

    return f'{position_str}', 0


def get_trackname(metadata):
    title = metadata.get('xesam:title', '')
    artist = ', '.join(metadata.get('xesam:artist', ''))

    if not artist:
        return title

    return '{} - {}'.format(artist, title)


#TODO: percentage underline
#TODO: track volume and print if changed
def get_output(player):
    if not player:
        return ''

    output = ''
    metadata = player.props.metadata.unpack()
    position_str, percent = get_position_info(player.props.position, metadata)

    output += STATUS_ICONS.get(player.get_property('playback-status'))
    output += ' '
    output += f"[{player.get_property('player-name')}]"
    output += f'[{position_str}]'
    output += ' '
    output += get_trackname(metadata)

    return output


def on_status_change(player):
    global previous_output
    output = ljust_clip(get_output(player), output_len)
    if output != previous_output:
        print(output, flush=True)
        previous_output = output