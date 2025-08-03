{
  lib,
  fetchurl,
  fetchFromGitHub,
  stdenvNoCC,
  docker,
  installShellFiles,
  _7zz,
}:

stdenvNoCC.mkDerivation (
  finalAttrs:
  let
    sources = {
      "aarch64-darwin" = {
        url = "https://cdn-updates.orbstack.dev/arm64/OrbStack_v${finalAttrs.version}_arm64.dmg";
        sha256 = "1p3qazha4q1ihqa4154jynp11kw9vqw4cyvpkdad4c9dcy9a6fzz";
      };
      "x86_64-darwin" = {
        url = "https://cdn-updates.orbstack.dev/amd64/OrbStack_v${finalAttrs.version}_amd64.dmg";
        sha256 = "07vkbg8n116nyfxzppj0w4z37v4sgz2cvvfhlwscylq3x4lr7cx0";
      };
    };

  in
  {
    pname = "orbstack";
    version = "1.11.3_19358";

    src = fetchurl {
      inherit (sources.${stdenvNoCC.hostPlatform.system}) url sha256;
    };

    sourceRoot = "OrbStack.app";

    nativeBuildInputs = [
      installShellFiles
      _7zz
    ];

    unpackPhase = ''
      7zz x -snld "$src"
    '';

    installPhase = ''
      mkdir -p "$out/Applications/${finalAttrs.sourceRoot}"
      cp -R . "$out/Applications/${finalAttrs.sourceRoot}"

      mkdir -p "$out/bin"
      ln -s "$out/Applications/${finalAttrs.sourceRoot}/Contents/MacOS/bin/orb" "$out/bin/orb"
      ln -s "$out/Applications/${finalAttrs.sourceRoot}/Contents/MacOS/bin/orbctl" "$out/bin/orbctl"
      ln -s "$out/Applications/${finalAttrs.sourceRoot}/Contents/MacOS/xbin/docker" "$out/bin/docker"
      ln -s "$out/Applications/${finalAttrs.sourceRoot}/Contents/MacOS/xbin/docker-buildx" "$out/bin/docker-buildx"
      ln -s "$out/Applications/${finalAttrs.sourceRoot}/Contents/MacOS/xbin/docker-compose" "$out/bin/docker-compose"
      ln -s "$out/Applications/${finalAttrs.sourceRoot}/Contents/MacOS/xbin/docker-credential-osxkeychain" "$out/bin/docker-credential-osxkeychain"

      # completion for docker
      installShellCompletion --bash "$out/Applications/${finalAttrs.sourceRoot}/Contents/Resources/completions/docker.bash"
      installShellCompletion --fish "$out/Applications/${finalAttrs.sourceRoot}/Contents/Resources/completions/docker.fish"
      installShellCompletion --zsh  "$out/Applications/${finalAttrs.sourceRoot}/Contents/Resources/completions/zsh/_docker"
    '';

    meta = {
      description = "Fast, light, simple Docker containers & Linux machines for macOS";
      homepage = "https://orbstack.dev/";
      license = lib.licenses.unfree;
      maintainers = with lib.maintainers; [ sudosubin ];
      platforms = builtins.attrNames sources;
    };
  }
)
