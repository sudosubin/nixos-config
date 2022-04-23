final: { lib, stdenv, fetchFromGitHub, ... }@prev:

let
  rev = "4b5c2f354107d076b315da2347cda4937d584716";

  buildSymlinks = prev.runCommand "build-symlinks" { } ''
    mkdir -p $out/bin
    ln -s /usr/bin/xcrun /usr/bin/xcodebuild /usr/bin/tiffutil /usr/bin/qlmanage $out/bin
  '';

in
{
  yabai = prev.yabai.overrideDerivation (attrs: rec {
    pname = "yabai";
    version = lib.substring 0 7 rev;

    src = fetchFromGitHub {
      inherit rev;
      owner = "koekeishiya";
      repo = pname;
      sha256 = "sha256-YviC2GkuFcV/VLsb/dRuPvxuSkriSCGHNbGUH2Dz1sY=";
    };

    nativeBuildInputs = attrs.nativeBuildInputs ++ [ buildSymlinks ];
  });
}
