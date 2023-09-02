final: { lib, fetchurl, stdenvNoCC, unzip, ... }@prev:

let
  version = "2.12.0";

  sources = {
    "aarch64-darwin" = {
      url = "https://github.com/hadolint/hadolint/releases/download/v${version}/hadolint-Darwin-x86_64";
      sha256 = "09yd84yzqga3gxb29gk9ir4gfrdq6pcgrgnflwwmqr4imgy7lnra";
    };
    "x86_64-darwin" = {
      url = "https://github.com/hadolint/hadolint/releases/download/v${version}/hadolint-Darwin-x86_64";
      sha256 = "09yd84yzqga3gxb29gk9ir4gfrdq6pcgrgnflwwmqr4imgy7lnra";
    };
    "aarch64-linux" = {
      url = "https://github.com/hadolint/hadolint/releases/download/v${version}/hadolint-Linux-arm64";
      sha256 = "1xjxgjw1r5ip9jgpxv7724zh5vqaz4wb4ppih4c9acwzy4dmb62p";
    };
    "x86_64-linux" = {
      url = "https://github.com/hadolint/hadolint/releases/download/v${version}/hadolint-Linux-x86_64";
      sha256 = "042hsmi87awah87ckxab4ihhvz67f49daj7sfixy29y4brg6vpjn";
    };
  };

in
# https://github.com/NixOS/nixpkgs/commit/72573db36b517
{
  hadolint = stdenvNoCC.mkDerivation rec {
    inherit version;

    pname = "hadolint";

    src = fetchurl {
      inherit (sources.${stdenvNoCC.hostPlatform.system}) url sha256;
    };

    dontUnpack = true;

    installPhase = ''
      mkdir -p $out/bin
      cp $src $out/bin/hadolint
      chmod +x $out/bin/hadolint
    '';

    meta = with lib; {
      homepage = "https://github.com/hadolint/hadolint";
      description = "Dockerfile Linter JavaScript API";
      license = licenses.gpl3Only;
      platforms = platforms.unix;
      maintainers = [ maintainers.sudosubin ];
    };
  };
}
