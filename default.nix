{ stdenv, buildPythonApplication, fetchFromGitHub, git, runCommand
, glibcLocales, gobject-introspection
, dbus-python, glib, playerctl, pygobject3
, localSrc ? true
}:

assert stdenv.lib.versionAtLeast playerctl.version "2.0";

let
  smartPathFilter = basePath: f: let
      inherit (stdenv.lib) stringLength substring;
      relPath = substring (stringLength basePath) (-1); in
    p: let path = relPath (toString p);
      dir = dirOf path; baseName = baseNameOf path; in
    type: !(f path dir baseName type);
  smartPath = args: builtins.path (args // {
    ${if args ? filter then "filter" else null} =
      smartPathFilter (toString args.path) args.filter;
  });
in

buildPythonApplication rec {
  pname = "playerctlctl";
  # to get date: TZ=UTC git show -s --format=%cd --date=short-local
  version = let revDate = if localSrc then
    builtins.readFile (runCommand "playerctlctl-git-rev-date" {
      src = smartPath {
        path = ./.git; name = "${pname}-local-rev-date-gitdir";
        filter = path: dir: baseName: type:
          path == "/index" ||
          path == "/logs" ||
        false;
      };
      buildInputs = [ git ];
    } ''
      TZ=UTC git --git-dir=$src show -s --format="format:%cd" --date=short-local > "$out"
    '')
  else "2019-04-05"; in "0.1.0-${revDate}";

  src = if !localSrc then fetchFromGitHub {
    owner = "udf";
    repo = "playerctlctl";
    rev = "f7cfb130878b1e1ade29d508dbaa455f2d871497";
    sha256 = "0000000000000000000000000000000000000000000000000000";
  } else smartPath {
    path = ./.; name = "${pname}-local";
    filter = path: dir: baseName: type:
      (type == "symlink" && stdenv.lib.hasPrefix "/result" path) ||
      path == "/.git" ||
      baseName == "/__pycache__" ||
      baseName == "/.vscode" ||
    false;
  };

  format = "flit";

  buildInputs = [
    gobject-introspection # populate GI_TYPELIB_PATH
    playerctl
  ];
  propagatedBuildInputs = [
    glib
    playerctl
    pygobject3
  ];

  checkInputs = [
    glibcLocales
  ];

  makeWrapperArgs = [
    ''--prefix GI_TYPELIB_PATH ':' "$GI_TYPELIB_PATH"''
  ];

  meta = with stdenv.lib; {
    description = "A daemon to make controlling multiple players easier";
    longDescription = ''
      Playerctlctl is a daemon that talks to playerctl (a command-line utility
      for controling media players that implement MPRIS (a standard D-Bus
      interface for controling media players)) to make managing multiple open
      players easier.
    '';
    homepage = https://github.com/udf/playerctlctl;
    license = with licenses; isc;
    maintainers = with maintainers; [ bb010g ];
    platforms = platforms.unix;
  };
}
