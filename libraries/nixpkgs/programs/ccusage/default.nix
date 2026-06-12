{
  fetchFromGitHub,
  fetchurl,
  lib,
  nix-update-script,
  rustPlatform,
  versionCheckHook,
}:

rustPlatform.buildRustPackage (finalAttrs: {
  pname = "ccusage";
  version = "20.0.11";

  src = fetchFromGitHub {
    owner = "ryoppippi";
    repo = "ccusage";
    tag = "v${finalAttrs.version}";
    hash = "sha256-1JQubdqW3XQwF2ZZTXld5SHopBKcjKmqO/RXWZ4T3HU=";
  };

  cargoRoot = "rust";
  buildAndTestSubdir = finalAttrs.cargoRoot;
  cargoHash = "sha256-y+AGi2hduEbexGzdnVoTv7GEkl+nPFDFyhSzZY1xRjs=";

  litellmPricingJson = fetchurl {
    url = "https://raw.githubusercontent.com/BerriAI/litellm/e59e34bed3670a6894d43129c2af16af28057d03/model_prices_and_context_window.json";
    hash = "sha256-aPue4NpPpTKAtAYCI8S8ojmVCDtYr+mxwtYkOASEg3w=";
  };

  nativeBuildInputs = [
    versionCheckHook
  ];

  env.CCUSAGE_PRICING_JSON_PATH = "${finalAttrs.litellmPricingJson}";

  doInstallCheck = true;

  passthru.updateScript = nix-update-script { };

  meta = {
    description = "CLI tool for analyzing Claude Code usage from local JSONL files";
    homepage = "https://ccusage.com";
    changelog = "https://github.com/ryoppippi/ccusage/releases/tag/v${finalAttrs.version}";
    license = lib.licenses.mit;
    platforms = lib.platforms.all;
    maintainers = with lib.maintainers; [ sudosubin ];
    mainProgram = "ccusage";
  };
})
