final: { lib, fetchzip, stdenvNoCC, ... }@prev:

let
  inherit (stdenvNoCC.hostPlatform) isDarwin isAarch64;

in
{
  yabai = prev.yabai.overrideDerivation (attrs: lib.optionals (isDarwin && isAarch64) rec {
    pname = "yabai";
    version = "5.0.3";
    name = "${pname}-${version}";

    src = fetchzip {
      url = "https://github.com/koekeishiya/yabai/releases/download/v${version}/yabai-v${version}.tar.gz";
      sha256 = "sha256-dnUrdCbEN/M4RAr/GH3x10bfr2TUjuomxIUStFK7X9M=";
    };
  });
}
