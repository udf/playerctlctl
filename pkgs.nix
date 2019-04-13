{ pkgs ? import <nixpkgs> { } }:

let
  gobject-introspection = pkgs: pkgs.gobjectIntrospection or pkgs.gobject-introspection;
in rec {
  # tools

  ## tools.audio

  playerctlctl = pkgs.python3Packages.callPackage ./. {
    gobject-introspection = gobject-introspection pkgs;
  };
}
