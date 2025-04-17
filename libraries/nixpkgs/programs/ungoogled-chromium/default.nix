{
  lib,
  stdenvNoCC,
  fetchurl,
  _7zz,
}:

let
  version = "135.0.7049.84-1.1";
  hdiutil = "/usr/bin/hdiutil";

  sources = {
    "aarch64-darwin" = {
      url = "https://github.com/ungoogled-software/ungoogled-chromium-macos/releases/download/${version}/ungoogled-chromium_${version}_arm64-macos.dmg";
      sha256 = "0a5xzycizppavagzb05v4vhbgw5vzc404cbac9k4awnxpqmf6kqr";
    };
    "x86_64-darwin" = {
      url = "https://github.com/ungoogled-software/ungoogled-chromium-macos/releases/download/${version}/ungoogled-chromium_${version}_x86_64-macos.dmg";
      sha256 = "0wzaz5bxh1bqkr0bl4cswm34hszv975lkajs7xymagw38wal315a";
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
