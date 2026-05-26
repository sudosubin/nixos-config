{
  fetchFromGitHub,
  lib,
  nix-update-script,
  stdenvNoCC,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "pi-promptsmith";
  version = "0.4.0";

  src = fetchFromGitHub {
    owner = "ayagmar";
    repo = "pi-promptsmith";
    rev = "v${finalAttrs.version}";
    hash = "sha256-eBMzQbmbi8shudqyz96DHAnoNiWYcD+ACJKq/sWhzYQ=";
  };

  patches = [
    ./use-agent-dir.patch
  ];

  dontBuild = true;

  installPhase = ''
    runHook preInstall
    mkdir -p $out
    cp -r LICENSE README.md package.json src $out/
    runHook postInstall
  '';

  passthru.updateScript = nix-update-script { };

  meta = {
    description = "Intent-aware prompt rewriter and execution-contract compiler for Pi";
    homepage = "https://github.com/ayagmar/pi-promptsmith";
    license = lib.licenses.mit;
    maintainers = with lib.maintainers; [ sudosubin ];
  };
})
