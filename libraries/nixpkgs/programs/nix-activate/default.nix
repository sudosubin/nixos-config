{
  lib,
  rustPlatform,
  fetchFromGitHub,
  pkg-config,
  openssl,
  stdenvNoCC,
}:

rustPlatform.buildRustPackage (finalAttrs: {
  pname = "nix-activate";
  version = "0.1.0";

  src = fetchFromGitHub {
    owner = "sudosubin";
    repo = finalAttrs.pname;
    rev = "c2336a6";
    sha256 = "sha256-BiFwkWfvuPf64SX9PTZllOJq0RKJbbh2vlMOIlEzEkI=";
  };

  cargoHash = "sha256-xO753cda/cUm/Z6tgC3BC3xRX2gHmTsvjOCITvbxWfU=";

  nativeBuildInputs = [ pkg-config ];
  buildInputs = [ openssl ];

  meta = with lib; {
    description = "A simple script to enable nix flake direnv from current directory or external flake repository";
    homepage = "https://github.com/sudosubin/nix-activate";
    license = lib.licenses.mit;
    maintainers = with lib.maintainers; [ sudosubin ];
    platforms = lib.platforms.unix;
    mainProgram = "nix-activate";
  };
})
