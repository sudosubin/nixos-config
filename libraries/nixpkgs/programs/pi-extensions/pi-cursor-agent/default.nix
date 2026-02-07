{
  buildNpmPackage,
  fetchFromGitHub,
  lib,
  nix-update-script,
}:

buildNpmPackage (finalAttrs: {
  pname = "pi-cursor-agent";
  version = "0.1.1";

  src = fetchFromGitHub {
    owner = "sudosubin";
    repo = "pi-cursor-agent";
    tag = "v${finalAttrs.version}";
    hash = "sha256-AyEwKjsSp2thwSSGRFwGhEwZrX1msPGRpoI+4Wvt3rY=";
  };

  npmDepsHash = "sha256-MzUADdICV7++srCSuQx+BwpcNshsChrrHkVHkxN+mdo=";

  dontNpmBuild = true;

  installPhase = ''
    runHook preInstall
    mkdir -p $out
    cp -r package.json src node_modules $out/
    runHook postInstall
  '';

  passthru.updateScript = nix-update-script { };

  meta = {
    description = "Cursor Agent provider extension for pi";
    homepage = "https://github.com/sudosubin/pi-cursor-agent";
    license = lib.licenses.mit;
    maintainers = with lib.maintainers; [ sudosubin ];
  };
})
