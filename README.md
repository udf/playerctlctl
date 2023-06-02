# Note
This project is archived and deprecated in favour of playerctld, despite [all][playerctl-garbage1] [its][playerctl-garbage2] [flaws][playerctl-garbage3].  
I recommend using [a script like this][music-script] to correctly follow the current player because of how broken playerctl's follow mode is.

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

I made this to replace [my old statusbar script][dotfiles-polybar-music], so you
need to make your own outputter module for your own bar (see the `bar_status` module).

After you get the daemon running correctly, preferably using the included
`playerctlctl.service` unit you should set up hotkeys to talk to playerctlctl.

I use [socat][] to do this, see [my playerctlctlctl helper script][playerctlctlctl].

[My i3 bindings][dotfiles-i3-bindings] are an example of using the helper script.

If you want information about what commands you can run, look at the
`Commands` class in `commands.py`. Note that you can run a function on the [PlayerctlPlayer][api-player] object by prefixing it with `player.`
(for example, `player.next`).


[api-player]: https://dubstepdish.com/playerctl/PlayerctlPlayer.html
[api-player-manager]: https://dubstepdish.com/playerctl/PlayerctlPlayerManager.html
[dotfiles-i3-bindings]: https://github.com/udf/dotfiles-stow/blob/b80cde9df64293bf877e4da2b66592ce81955892/home/.config/i3/config_main#L47-L66
[dotfiles-polybar-music]: https://github.com/udf/dotfiles-stow/blob/5444705006ee8d416e96038f0bc7d2d15fc75096/home/.config/polybar/music.py
[license]: ./LICENSE.txt
[mpris]: https://specifications.freedesktop.org/mpris-spec/latest/
[playerctl]: https://github.com/acrisci/playerctl
[playerctlctl]: https://github.com/udf/playerctlctl
[playerctlctlctl]: https://github.com/udf/dotfiles-stow/blob/b80cde9df64293bf877e4da2b66592ce81955892/home/scripts/playerctlctlctl
[socat]: http://www.dest-unreach.org/socat/
[spdx]: https://spdx.org/licenses/
[spdx-isc]: https://spdx.org/licenses/ISC.html
[playerctl-garbage1]: https://github.com/altdesktop/playerctl/issues/247
[playerctl-garbage2]: https://github.com/altdesktop/playerctl/issues/270
[playerctl-garbage3]: https://github.com/altdesktop/playerctl/issues/304
[music-script]: https://github.com/udf/dotfiles-stow/commit/2c7571a8171df8ba7e9a8c1b745fbae70248cb7f#diff-c78e3272bfe6acc0f6a39f499c71b8ef7a5fdb60eca439be1b05c0d9a3f0e82c