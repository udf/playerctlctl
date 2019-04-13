# Playerctlctl

[Playerctlctl][] is a daemon that talks to [playerctl][] (a command-line
utility for controling media players that implement [MPRIS][] (a standard
D-Bus interface for controling media players)) to make managing multiple open
players easier.

Licensed under [the ISC license][license] ([SPDX][] ID [ISC][spdx-isc]).


## Why tho

The playerctl utility is stateless and talks to the "most recent" player. This
can get annoying if you open more than one player.


## How tho

Playerctl also offers a GLib interface, which includes a neat
[PlayerManager][api-player-manager] class. This script wraps that class with a
Unix socket server and functionality to select/talk to the currently active
player.


## Usage

Firstly, you should get playerctl running on your system and talking to a
player of your choice.

I made this to replace [my statusbar script][dotfiles-polybar-music], so you
need to make your own outputter module for your own bar.

After you get the output appearing correctly in your bar (anywhere, really)
you need to set up hotkeys to talk to playerctlctl.

I use [socat][] to do this:
```sh
# command and args are NUL delimited
printf '%s\0' command args ... | socat - UNIX-CONNECT:/tmp/playerctlctl1000
```

[My i3 bindings][dotfiles-i3-bindings] and
[the helper `playerctlctlctl` script][playerctlctlctl] can be found at their
respective links.

If you want information about what commands you can run, look at the
`COMMAND_ARGS` dictionary in `playerctlctl` and the docstrings in
`playerctlctl.commands`. Note that if a command doesn't exist in `.commands`,
then playerctlctl tries to run your input function directly on the
[PlayerctlPlayer][api-player] object.


[api-player]: https://dubstepdish.com/playerctl/PlayerctlPlayer.html
[api-player-manager]: https://dubstepdish.com/playerctl/PlayerctlPlayerManager.html
[dotfiles-i3-bindings]: https://github.com/udf/dotfiles-stow/blob/36faeb6ef6239a784931e24871a08eae29021fc7/home/.config/i3/config_main#L50-L59
[dotfiles-polybar-music]: https://github.com/udf/dotfiles-stow/blob/5444705006ee8d416e96038f0bc7d2d15fc75096/home/.config/polybar/music.py
[license]: ./LICENSE.txt
[mpris]: https://specifications.freedesktop.org/mpris-spec/latest/
[playerctl]: https://github.com/acrisci/playerctl
[playerctlctl]: https://github.com/udf/playerctlctl
[playerctlctlctl]: https://github.com/udf/dotfiles-stow/blob/42c046d6615f825ba8b194d814d93bdf37052952/home/scripts/playerctlctlctl
[socat]: http://www.dest-unreach.org/socat/
[spdx]: https://spdx.org/licenses/
[spdx-isc]: https://spdx.org/licenses/ISC.html
