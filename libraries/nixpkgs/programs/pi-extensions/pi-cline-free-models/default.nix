{
  fetchFromGitHub,
  lib,
  nix-update-script,
  stdenvNoCC,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "pi-cline-free-models";
  version = "0.1.7";

  src = fetchFromGitHub {
    owner = "ditfetzt";
    repo = "pi-cline-free-models";
    tag = "v${finalAttrs.version}";
    hash = "sha256-yhCV0umPH5+5r/DajjkCHuMUpmutaLRsDJE7udJ6+LQ=";
  };

  postPatch = ''
    sed -i '/ctx\.ui\.notify.*Cline extension updated/d' index.ts
  '';

  dontBuild = true;

  installPhase = ''
    runHook preInstall
    mkdir -p $out
    cp -r package.json index.ts $out/
    runHook postInstall
  '';

  passthru.updateScript = nix-update-script { };

  meta = {
    description = "Use Cline models as a provider in pi";
    homepage = "https://github.com/ditfetzt/pi-cline-free-models";
    license = lib.licenses.mit;
    maintainers = with lib.maintainers; [ sudosubin ];
  };
})
