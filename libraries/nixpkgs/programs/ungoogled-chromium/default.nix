{ lib, stdenvNoCC, fetchurl, _7zz }:

let
  version = "134.0.6998.165-1.1";
  hdiutil = "/usr/bin/hdiutil";

  sources = {
    "aarch64-darwin" = {
      url = "https://github.com/ungoogled-software/ungoogled-chromium-macos/releases/download/${version}/ungoogled-chromium_${version}_arm64-macos.dmg";
      sha256 = "13sfhn2n53wmaw5rimljh7049y24zi54prgis1shwg9b8hfvbds2";
    };
    "x86_64-darwin" = {
      url = "https://github.com/ungoogled-software/ungoogled-chromium-macos/releases/download/${version}/ungoogled-chromium_${version}_x86_64-macos.dmg";
      sha256 = "0cds85rm4qr6pcsncs48alk8s0fdjyas96nn5hysgn764nis1mkv";
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

  meta = with lib; {
    homepage = "https://ungoogled-software.github.io/";
    description = "Google Chromium, sans integration with Google";
    license = licenses.bsd3;
    platforms = builtins.attrNames sources;
    maintainers = [ maintainers.sudosubin ];
  };

}
