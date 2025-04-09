{
  lib,
  rustPlatform,
  fetchFromGitHub,
  pkg-config,
  openssl,
  stdenvNoCC,
}:

rustPlatform.buildRustPackage rec {
  pname = "nix-activate";
  version = "0.1.0";

  src = fetchFromGitHub {
    owner = "sudosubin";
    repo = pname;
    rev = "5debfbe";
    sha256 = "sha256-mSj0xgsYK6QBRA3MAd1L9a91xEkt82EHKs4mQtE+lw0=";
  };

  useFetchCargoVendor = true;
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
}
