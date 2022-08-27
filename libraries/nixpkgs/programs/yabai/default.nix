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
    version = "4.0.2";

    src = fetchFromGitHub {
      owner = "koekeishiya";
      repo = pname;
      rev = "v${version}";
      sha256 = "sha256-DXDdjI4kkLcRUNtMoSu7fJ0f3fUty88o5ZS6lJz0cGU=";
    };

    nativeBuildInputs = attrs.nativeBuildInputs ++ [ buildSymlinks ];
  });
}
