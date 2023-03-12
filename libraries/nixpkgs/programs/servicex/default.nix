final: { lib, stdenvNoCC, fetchzip, makeWrapper, grpcurl, ... }@prev:

let
  version = "0.40.0";

  sources = {
    darwin = {
      url = "https://github.com/servicex-sh/httpx/releases/download/v${version}/httpx-${version}-x86_64-apple-darwin.tar";
      sha256 = "sha256-+SdxlBjBiKSUMrIykDy6eAiwkK+F0sxwP0qP+PLVjMM=";
    };

    linux = {
      url = "https://github.com/servicex-sh/httpx/releases/download/v${version}/httpx-linux-x86_64.zip";
      sha256 = "";
    };
  };

in
{
  servicex = stdenvNoCC.mkDerivation rec {
    pname = "servicex";
    inherit version;

    src = fetchzip (if stdenvNoCC.isDarwin then sources.darwin else sources.linux);

    nativeBuildInputs = [ makeWrapper ];

    installPhase = ''
      mkdir -p $out/bin
      cp bin/httpx $out/bin/servicex
      runHook postInstall
    '';

    postInstall = ''
      wrapProgram $out/bin/servicex --prefix PATH : ${lib.makeBinPath [ grpcurl ]}
    '';

    meta = with lib; {
      homepage = "https://github.com/servicex-sh/httpx";
      description = "httpx - CLI to run HTTP file";
      license = "Apache-2.0";
      platforms = platforms.unix;
      maintainers = [ maintainers.sudosubin ];
    };
  };
}
