{ lib, fetchurl, fetchFromGitHub, stdenvNoCC, docker, installShellFiles, _7zz }:

let
  version = "1.7.5_18165";
  hdiutil = "/usr/bin/hdiutil";

  sources = {
    "aarch64-darwin" = {
      url = "https://cdn-updates.orbstack.dev/arm64/OrbStack_v${version}_arm64.dmg";
      sha256 = "01hb95jrrm7ps4mn83p1983pfyaxdq0k48611i9hj9pz6bwl19xr";
    };
    "x86_64-darwin" = {
      url = "https://cdn-updates.orbstack.dev/amd64/OrbStack_v${version}_amd64.dmg";
      sha256 = "1c0lbmsqb0rn09179s6ax05dla0b414l0likl36rcr52kvy0dv37";
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
