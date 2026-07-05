{
  fetchFromGitHub,
  lib,
  nix-update-script,
  rustPlatform,
}:

rustPlatform.buildRustPackage (finalAttrs: {
  pname = "querypie-cli";
  version = "0.1.1";

  src = fetchFromGitHub {
    owner = "sudosubin";
    repo = "querypie-cli";
    rev = "v${finalAttrs.version}";
    hash = "sha256-aLTMWX4ZGRvz1xxt79GOmHw04Vkl9luA8u9e6MQx20c=";
  };

  cargoHash = "sha256-irBRhgJ1Yb/QjG1XH21rTejVLAG6JQAydwYAdmRa8TA=";

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
