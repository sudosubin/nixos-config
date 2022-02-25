final: { lib, stdenv, fetchFromGitHub, ... }@prev:

let
  rev = "916d9133f9d13fb38678baa3d0adf3cfb9dff003";

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
      sha256 = "sha256-RFEuVIMP9+HXnkSPRobCATzg9fsu48zoAFq7AqodLaQ=";
    };

    nativeBuildInputs = attrs.nativeBuildInputs ++ [ buildSymlinks ];

    postInstall = ''
      $out/bin/yabai --install-sa
      $out/bin/yabai --load-sa
    '';
  });
}
