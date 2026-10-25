{
  fetchFromGitHub,
  lib,
  nix-update-script,
  stdenvNoCC,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "pi-subagent";
  version = "1.4.0";

  src = fetchFromGitHub {
    owner = "earendil-works";
    repo = "pi";
    rev = "v${finalAttrs.version}";
    hash = "sha256-N9NOpiiZTbOMDMV+CxvJAgtLjJJ1/8NJBGS0cFHkhsc=";
  };

  dontBuild = true;

  installPhase = ''
    runHook preInstall
    mkdir -p $out
    cp -r packages/coding-agent/examples/extensions/subagent/. $out/
    install -m644 LICENSE $out/LICENSE
    runHook postInstall
  '';

  passthru.updateScript = nix-update-script { };

  meta = {
    description = "Subagent delegation extension for pi";
    homepage = "https://github.com/earendil-works/pi/tree/main/packages/coding-agent/examples/extensions/subagent";
    license = lib.licenses.mit;
    maintainers = with lib.maintainers; [ sudosubin ];
  };
})
