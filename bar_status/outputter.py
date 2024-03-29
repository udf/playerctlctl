import asyncio
import time
import logging
import traceback

from tinyrpc import RPCError

logger = logging.getLogger('outputter')

# These icons are from nerd-fonts
# https://github.com/ryanoasis/nerd-fonts
STATUS_ICONS = {
    'paused': '',
    'playing': '',
    'stopped': ''
}
prev_output = ''


class AutoHideModule:
    def __init__(self, fmt='{}', hidden_fmt='{}', timeout=5):
        self.fmt = fmt
        self.hidden_fmt = hidden_fmt
        self.timeout = timeout
        self.prev_change = 0
        self.prev_output = ''

    def get_output(self, val, hidden_text=''):
        output = self.fmt.format(val)
        if output != self.prev_output:
            self.prev_change = time.time()
        self.prev_output = output
        if time.time() - self.prev_change < self.timeout:
            return output
        return self.hidden_fmt.format(hidden_text)


volume_module = AutoHideModule('[ {}%]', timeout=5)
player_name_module = AutoHideModule('[{}]', '[{}]', timeout=5)


def ljust_clip(string, n):
    if len(string) > n:
        return string[:n-3] + '...'
    return string.ljust(n)


def get_position_info(position, metadata):
    def fmt(seconds):
        if seconds is None:
            return '--:--'
        prefix = '-' if seconds < 0 else ''
        hours, rem = divmod(round(abs(seconds)), 3600)
        minutes, seconds = divmod(rem, 60)
        if hours:
            return f'{prefix}{hours:02}:{minutes:02}:{seconds:02}'
        return f'{prefix}{minutes:02}:{seconds:02}'

    position_str = fmt(position)
    duration = metadata.get('mpris:length', 0) / 1000000

    if duration:
        return f'{position_str}/{fmt(duration)}', max(position, 0) / duration

    return f'{position_str}', 0


def get_trackname(metadata):
    title = metadata.get('xesam:title', '')
    artist = metadata.get('xesam:artist', '')
    url = metadata.get('xesam:url', '')

    if not title:
        return url.split('/')[-1]
    if not artist:
        return title
    if isinstance(artist, list):
        artist = ', '.join(artist)

    return f'{artist} - {title}'


async def get_output(rpc, max_length):
    player_instance = await rpc.do_request('ctl_get_instance')
    if not player_instance:
        return ' ' * max_length

    output = ''
    metadata = await rpc.do_request('get_all_metadata')
    try:
        position = await rpc.do_request('get_position')
    except RPCError:
        position = None
    position_str, percent = get_position_info(position, metadata)

    # Status icon
    output += STATUS_ICONS.get(await rpc.do_request('get_status'), '')
    output += ' '

    # Player name
    player_name = await rpc.do_request('ctl_get_name')
    output += player_name_module.get_output(player_instance, player_name)

    # Position
    output += f'[{position_str}]'

    # Volume
    volume = round(await rpc.do_request('get_volume') * 100)
    output += volume_module.get_output(volume)

    # Track name
    output += ' ' + get_trackname(metadata)

    # Left-justify/clip output
    output = ljust_clip(output, max_length)

    # Add underline tags to show player position
    end_underline_i = round(percent * max_length)
    output = '%{u#fff}' + output[:end_underline_i] + '%{-u}' + output[end_underline_i:]

    return output


async def print_output(rpc, max_length):
    global prev_output

    output = await get_output(rpc, max_length)
    if output != prev_output:
        print(output, flush=True)
    prev_output = output


def print_text(text, max_length):
    global prev_output
    text = '%{u#cc6666}' + ljust_clip(f' {text}', max_length)
    if text != prev_output:
        print(text, flush=True)
    prev_output = text