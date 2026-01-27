{
  fetchFromGitHub,
  kotlin-lsp,
  lib,
  makeWrapper,
  nix-update-script,
  rustPlatform,
}:

rustPlatform.buildRustPackage (finalAttrs: {
  pname = "kotlin-lsp-wrapper";
  version = "0-unstable-2025-10-13";

  src = fetchFromGitHub {
    owner = "Alacho2";
    repo = "kotlin-lsp-proxy";
    rev = "11cb77b5edbf9f4bf8677f2725d2a26c8bc04bee";
    hash = "sha256-vG8iQ5Jf4ZuDskzr8/3CSbL0UOGQVPEj7kTjyLVVPKQ=";
  };

  cargoHash = "sha256-W1Vb2XPhk2kLt2Oj4+F7AxEsap7fEfi58V/8ooDAl+A=";

  postUnpack = ''
    cp ${./Cargo.lock} $sourceRoot/Cargo.lock
  '';

  nativeBuildInputs = [ makeWrapper ];

  postInstall = ''
    wrapProgram $out/bin/kotlin-lsp-wrapper \
      --suffix PATH : ${lib.makeBinPath [ kotlin-lsp ]}
  '';

  passthru.updateScript = nix-update-script {
    extraArgs = [ "--version=branch" ];
  };

  meta = {
    description = "Just a wrapper for the kotlin-lsp ";
    homepage = "https://github.com/Alacho2/kotlin-lsp-proxy";
    license = lib.licenses.unlicense;
    maintainers = with lib.maintainers; [ sudosubin ];
    mainProgram = "kotlin-lsp-wrapper";
  };
})
