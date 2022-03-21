final: { lib, stdenv, fetchFromGitHub, ... }@prev:

let
  rev = "a4030e771f76d4f135f5b830eedd7234592df51e";

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
      sha256 = "sha256-SwoXH6d0blE+S5i4n0Y9Q8AJuQAAaQs+CK3y1hAQoPU=";
    };

    nativeBuildInputs = attrs.nativeBuildInputs ++ [ buildSymlinks ];

    postInstall = ''
      $out/bin/yabai --install-sa
      $out/bin/yabai --load-sa
    '';
  });
}
