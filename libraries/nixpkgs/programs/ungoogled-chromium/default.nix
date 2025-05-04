{
  lib,
  stdenvNoCC,
  fetchurl,
  _7zz,
}:

let
  version = "136.0.7103.59-1.1";
  hdiutil = "/usr/bin/hdiutil";

  sources = {
    "aarch64-darwin" = {
      url = "https://github.com/ungoogled-software/ungoogled-chromium-macos/releases/download/${version}/ungoogled-chromium_${version}_arm64-macos.dmg";
      sha256 = "1xnq99crp9mr050d1j5vs0mwya4v9j51carw7v3zcv95azg4ngkm";
    };
    "x86_64-darwin" = {
      url = "https://github.com/ungoogled-software/ungoogled-chromium-macos/releases/download/${version}/ungoogled-chromium_${version}_x86_64-macos.dmg";
      sha256 = "036n532hf3l0ahlwvkz29kflgfpj8pqwj7wbwmkxq3x3h3063362";
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
