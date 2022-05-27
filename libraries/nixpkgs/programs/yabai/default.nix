final: { lib, stdenv, fetchFromGitHub, ... }@prev:

let
  buildSymlinks = prev.runCommand "build-symlinks" { } ''
    mkdir -p $out/bin
    ln -s /usr/bin/xcrun /usr/bin/xcodebuild /usr/bin/tiffutil /usr/bin/qlmanage $out/bin
  '';

in
{
  yabai = prev.yabai.overrideDerivation (attrs: rec {
    pname = "yabai";
    version = "4.0.1";

    src = fetchFromGitHub {
      owner = "koekeishiya";
      repo = pname;
      rev = "v${version}";
      sha256 = "sha256-H1zMg+/VYaijuSDUpO6RAs/KLAAZNxhkfIC6CHk/xoI=";
    };

    nativeBuildInputs = attrs.nativeBuildInputs ++ [ buildSymlinks ];
  });
}
