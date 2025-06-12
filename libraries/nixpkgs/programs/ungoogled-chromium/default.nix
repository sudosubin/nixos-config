{
  lib,
  stdenvNoCC,
  fetchurl,
  _7zz,
}:

let
  version = "137.0.7151.68-1.1";
  hdiutil = "/usr/bin/hdiutil";

  sources = {
    "aarch64-darwin" = {
      url = "https://github.com/ungoogled-software/ungoogled-chromium-macos/releases/download/${version}/ungoogled-chromium_${version}_arm64-macos.dmg";
      sha256 = "19q6w3ll580pgm6kfala704sixvinn8b46b1hij1lww16iw6c130";
    };
    "x86_64-darwin" = {
      url = "https://github.com/ungoogled-software/ungoogled-chromium-macos/releases/download/${version}/ungoogled-chromium_${version}_x86_64-macos.dmg";
      sha256 = "1vl1l7xpqw02wazmdipfrfd7pn1alzijb5xhj0d1ixsjzjssvnw6";
    };
  };

in
stdenvNoCC.mkDerivation rec {
  inherit version;

  pname = "ungoogled-chromium";

  src = fetchurl {
    inherit (sources.${stdenvNoCC.hostPlatform.system}) url sha256;
  };

  sourceRoot = "Chromium.app";

  nativeBuildInputs = [ _7zz ];

  unpackPhase = ''
    mkdir -p ./Applications
    ${hdiutil} attach -readonly -mountpoint mnt $src
    cp -r "mnt/${sourceRoot}" .
    ${hdiutil} detach -force mnt
  '';

  installPhase = ''
    runHook preInstall
    mkdir -p "$out/Applications/${sourceRoot}"
    cp -R . "$out/Applications/${sourceRoot}"
    runHook postInstall
  '';

  meta = {
    description = "Google Chromium, sans integration with Google";
    homepage = "https://ungoogled-software.github.io/";
    license = lib.licenses.bsd3;
    maintainers = with lib.maintainers; [ sudosubin ];
    platforms = builtins.attrNames sources;
  };

}
