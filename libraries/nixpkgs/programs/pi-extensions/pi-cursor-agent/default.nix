{
  buildNpmPackage,
  fetchFromGitHub,
  lib,
  nix-update-script,
}:

buildNpmPackage (finalAttrs: {
  pname = "pi-cursor-agent";
  version = "0.4.2";

  src = fetchFromGitHub {
    owner = "sudosubin";
    repo = "pi-frontier";
    rev = "${finalAttrs.pname}@${finalAttrs.version}";
    hash = "sha256-+HFW24WTY32TvAvN5SK5n7rYf02CSIm78bKBMH6iIVw=";
  };

  sourceRoot = "${finalAttrs.src.name}/pi-cursor-agent";

  npmDepsHash = "sha256-JDPTBQ8pW21N2oNJ+JwfmjF6fs/Tvwz0rKJW/ZoOVpc=";

  dontNpmBuild = true;

  installPhase = ''
    runHook preInstall
    mkdir -p $out
    cp -r package.json src node_modules $out/
    runHook postInstall
  '';

  passthru.updateScript = nix-update-script {
    extraArgs = [
      "--version-regex=pi-cursor-agent@(.+)"
    ];
  };

  meta = {
    description = "Cursor Agent provider extension for pi";
    homepage = "https://github.com/sudosubin/pi-frontier/tree/main/pi-cursor-agent";
    license = lib.licenses.mit;
    maintainers = with lib.maintainers; [ sudosubin ];
  };
})
