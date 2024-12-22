{ lib, fetchurl, fetchFromGitHub, stdenvNoCC, docker, installShellFiles, _7zz }:

let
  version = "1.9.2_18814";
  hdiutil = "/usr/bin/hdiutil";

  sources = {
    "aarch64-darwin" = {
      url = "https://cdn-updates.orbstack.dev/arm64/OrbStack_v${version}_arm64.dmg";
      sha256 = "0wmx8n3yxjs5s06m7hyrgkjsf97shlpann1pgw31avxgmwzrzlmc";
    };
    "x86_64-darwin" = {
      url = "https://cdn-updates.orbstack.dev/amd64/OrbStack_v${version}_amd64.dmg";
      sha256 = "00w8xkadalmf4sclp7bb79c3rjmrkp72h5w3sc3a41s2cs1aj3id";
    };
  };

in
stdenvNoCC.mkDerivation rec {
  inherit version;

  pname = "orbstack";

  src = fetchurl {
    inherit (sources.${stdenvNoCC.hostPlatform.system}) url sha256;
  };

  sourceRoot = "OrbStack.app";

  nativeBuildInputs = [ installShellFiles _7zz ];

  unpackPhase = ''
    7zz x -snld "$src"
  '';

  installPhase = ''
    mkdir -p "$out/Applications/${sourceRoot}"
    cp -R . "$out/Applications/${sourceRoot}"

    mkdir -p "$out/bin"
    ln -s "$out/Applications/${sourceRoot}/Contents/MacOS/bin/orb" "$out/bin/orb"
    ln -s "$out/Applications/${sourceRoot}/Contents/MacOS/bin/orbctl" "$out/bin/orbctl"
    ln -s "$out/Applications/${sourceRoot}/Contents/MacOS/xbin/docker" "$out/bin/docker"
    ln -s "$out/Applications/${sourceRoot}/Contents/MacOS/xbin/docker-buildx" "$out/bin/docker-buildx"
    ln -s "$out/Applications/${sourceRoot}/Contents/MacOS/xbin/docker-compose" "$out/bin/docker-compose"
    ln -s "$out/Applications/${sourceRoot}/Contents/MacOS/xbin/docker-credential-osxkeychain" "$out/bin/docker-credential-osxkeychain"

    # completion for docker
    installShellCompletion --bash "$out/Applications/${sourceRoot}/Contents/Resources/completions/docker.bash"
    installShellCompletion --fish "$out/Applications/${sourceRoot}/Contents/Resources/completions/docker.fish"
    installShellCompletion --zsh  "$out/Applications/${sourceRoot}/Contents/Resources/completions/zsh/_docker"
  '';

  meta = with lib; {
    homepage = "https://orbstack.dev/";
    description = "Fast, light, simple Docker containers & Linux machines for macOS";
    license = licenses.unfree;
    platforms = builtins.attrNames sources;
    maintainers = [ maintainers.sudosubin ];
  };
}
