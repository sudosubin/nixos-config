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
  version = "20.0.14";

  src = fetchFromGitHub {
    owner = "ryoppippi";
    repo = "ccusage";
    tag = "v${finalAttrs.version}";
    hash = "sha256-KtN0dJ183W9i9y+eyLl95WKXrtu7uF0D/sN6/hu6Sr4=";
  };

  cargoRoot = "rust";
  buildAndTestSubdir = finalAttrs.cargoRoot;
  cargoHash = "sha256-h3qXDzIu7Qv7/OnaVH9Fz3a3ZTChNS5JcaiHe/XG2eE=";

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
