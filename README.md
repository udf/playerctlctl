# Playerctlctl
[Playerctlctl](https://github.com/udf/playerctlctl) is a daemon that talks to
[Playerctl](https://github.com/acrisci/playerctl) (a command-line utility
for controling media players that implement [MPRIS](http://specifications.freedesktop.org/mpris-spec/latest/)
A standard D-Bus interface for controling media players))


# Why tho
The Playerctl command-line utility is stateless and talks to the "most recent"
player. This can get annoying if you open more than one player.


# How tho
Playerctl also offers a GLib interface, which includes a neat
[PlayerManager](https://dubstepdish.com/Playerctl/PlayerctlPlayerManager.html)
class.  
This script wraps that class with a unix socket server and functionality to
select/talk to the currently active player.


# Usage
Firstly, you should get Playerctl running on your system and talking to a
player of your choice.

I made this to replace [my statusbar script](https://github.com/udf/dotfiles-stow/blob/5444705006ee8d416e96038f0bc7d2d15fc75096/home/.config/polybar/music.py),
so you need to make your own outputter module for your own bar.

After you get the output appearing correctly
in your bar (anywhere, really) you need to setup hotkeys to talk to playerctlctl.

I use socat to do this:
```
$ socat - UNIX-CONNECT:/tmp/playerctlctl1000 <<< "command here"
```

You can find my i3 bindings for this [here](https://github.com/udf/dotfiles-stow/blob/36faeb6ef6239a784931e24871a08eae29021fc7/home/.config/i3/config_main#L50-L59).

If you need information about what commands you can run, look at this
dictionary.
