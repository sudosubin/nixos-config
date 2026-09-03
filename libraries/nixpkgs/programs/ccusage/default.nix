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
  version = "20.0.20";

  src = fetchFromGitHub {
    owner = "ryoppippi";
    repo = "ccusage";
    tag = "v${finalAttrs.version}";
    hash = "sha256-fMEun+cbIUWBJgH26FsY0xh9uq86ySZsiRpRgBqEUCk=";
  };

  cargoRoot = "rust";
  buildAndTestSubdir = finalAttrs.cargoRoot;
  cargoHash = "sha256-uKJlz37i/y2sCBHA12yY4pkjT6HOV9Nbw1ATyUsG+uY=";

  litellmPricingJson = fetchurl {
    url = "https://raw.githubusercontent.com/BerriAI/litellm/1a183efaa1a2108aed7e1bed8d445d93bd1aa60d/model_prices_and_context_window.json";
    hash = "sha256-p0U40u3BPh609nhw+8LuBQNTJubq7Q3FvOEdNyz/bmA=";
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
