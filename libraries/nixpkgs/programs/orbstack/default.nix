{ lib, fetchurl, fetchFromGitHub, stdenvNoCC, docker, docker-compose_1, installShellFiles }:

let
  version = "1.2.0_16496";
  hdiutil = "/usr/bin/hdiutil";

  completions = {
    docker = docker.src;
    docker-compose = docker-compose_1.out;
  };

  sources = {
    "aarch64-darwin" = {
      url = "https://cdn-updates.orbstack.dev/arm64/OrbStack_v${version}_arm64.dmg";
      sha256 = "0bjj19j2zic38s98m0glxiiiiz179vj9z6fps9s84k8lvs3qb9wr";
    };
    "x86_64-darwin" = {
      url = "https://cdn-updates.orbstack.dev/amd64/OrbStack_v${version}_amd64.dmg";
      sha256 = "10mjrc0yq732bxb11b0jd0k8w0yn2bv685dlczcfsnx53r89yrc1";
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

  nativeBuildInputs = [ installShellFiles ];

  unpackPhase = ''
    mkdir -p ./Applications
    ${hdiutil} attach -readonly -mountpoint mnt $src
    cp -r "mnt/${sourceRoot}" .
    ${hdiutil} detach -force mnt
  '';

  installPhase = ''
    mkdir -p "$out/Applications/${sourceRoot}"
    cp -R . "$out/Applications/${sourceRoot}"

    mkdir -p "$out/bin"
    ln -s "$out/Applications/${sourceRoot}/Contents/MacOS/xbin/docker" "$out/bin/docker"
    ln -s "$out/Applications/${sourceRoot}/Contents/MacOS/xbin/docker-buildx" "$out/bin/docker-buildx"
    ln -s "$out/Applications/${sourceRoot}/Contents/MacOS/xbin/docker-compose" "$out/bin/docker-compose"
    ln -s "$out/Applications/${sourceRoot}/Contents/MacOS/xbin/docker-credential-osxkeychain" "$out/bin/docker-credential-osxkeychain"
    ln -s "$out/Applications/${sourceRoot}/Contents/MacOS/bin/orb" "$out/bin/orb"
    ln -s "$out/Applications/${sourceRoot}/Contents/MacOS/bin/orbctl" "$out/bin/orbctl"

    # completion for docker
    installShellCompletion --bash ${completions.docker}/contrib/completion/bash/docker
    installShellCompletion --fish ${completions.docker}/contrib/completion/fish/docker.fish
    installShellCompletion --zsh  ${completions.docker}/contrib/completion/zsh/_docker

    # completion for docker-compose
    installShellCompletion --bash ${completions.docker-compose}/share/bash-completion/completions/docker-compose
    installShellCompletion --zsh ${completions.docker-compose}/share/zsh/site-functions/_docker-compose
  '';

  meta = with lib; {
    homepage = "https://orbstack.dev/";
    description = "Fast, light, simple Docker containers & Linux machines for macOS";
    license = licenses.unfree;
    platforms = builtins.attrNames sources;
    maintainers = [ maintainers.sudosubin ];
  };
}
