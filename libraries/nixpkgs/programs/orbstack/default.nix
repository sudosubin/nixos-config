final: { lib, fetchurl, fetchFromGitHub, stdenvNoCC, docker, installShellFiles, ... }@prev:

let
  version = "0.15.0_2207";
  hdiutil = "/usr/bin/hdiutil";
  completions = import ./completions.nix { pkgs = prev; };

  sources = {
    "aarch64-darwin" = {
      url = "https://cdn-updates.orbstack.dev/arm64/OrbStack_v${version}_arm64.dmg";
      sha256 = "1r6yxh8h37g4ia2z04rqhfnasnymkjhqa3lr21i2kcq6h6b6s2ri";
    };
    "x86_64-darwin" = {
      url = "https://cdn-updates.orbstack.dev/amd64/OrbStack_v${version}_amd64.dmg";
      sha256 = "0wxfwpppkdx75lnj59jlawiyy9fmg783pfi7i967pvg2hg86d1nl";
    };
  };

in
{
  orbstack = stdenvNoCC.mkDerivation rec {
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
      installShellCompletion --bash ${completions.docker-compose}/contrib/completion/bash/docker-compose
      installShellCompletion --fish ${completions.docker-compose}/contrib/completion/fish/docker-compose.fish
      installShellCompletion --zsh ${completions.docker-compose}/contrib/completion/zsh/_docker-compose
    '';

    meta = with lib; {
      homepage = "https://orbstack.dev/";
      description = "Fast, light, simple Docker containers & Linux machines for macOS";
      license = licenses.unfree;
      platforms = builtins.attrNames sources;
      maintainers = [ maintainers.sudosubin ];
    };
  };
}
