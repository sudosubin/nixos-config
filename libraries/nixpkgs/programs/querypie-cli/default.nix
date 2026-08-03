{
  fetchFromGitHub,
  lib,
  nix-update-script,
  rustPlatform,
}:

rustPlatform.buildRustPackage (finalAttrs: {
  pname = "querypie-cli";
  version = "0.2.3";

  src = fetchFromGitHub {
    owner = "sudosubin";
    repo = "querypie-cli";
    rev = "v${finalAttrs.version}";
    hash = "sha256-m7/A5cBeHFNY9dYG3yqES/k6cGbQaNTSZObiLp7GEwY=";
  };

  cargoHash = "sha256-E4Iun8kpKC96II3qpA23cMiNrpjVMVXq0vKE96Sg4PY=";

  passthru.updateScript = nix-update-script { };

  meta = {
    description = "Query QueryPie databases from the terminal with webview authentication";
    homepage = "https://github.com/sudosubin/querypie-cli";
    license = lib.licenses.mit;
    maintainers = with lib.maintainers; [ sudosubin ];
    mainProgram = "querypie";
    platforms = lib.platforms.darwin;
  };
})
