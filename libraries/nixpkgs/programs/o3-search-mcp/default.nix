{
  lib,
  stdenv,
  fetchurl,
  unzip,
  nodejs,
  pnpm,
}:

stdenv.mkDerivation (finalAttrs: {
  pname = "o3-search-mcp";
  version = "943dd37";

  src = fetchurl {
    url = "https://github.com/nacyot/o3-search-mcp/archive/${finalAttrs.version}.zip";
    sha256 = "1p2s7545fnna9r7rf6in9mqvd52bk8ka633xl2hrwx5467jmm3v3";
  };

  nativeBuildInputs = [
    unzip
    nodejs
    pnpm.configHook
  ];

  pnpmDeps = pnpm.fetchDeps {
    inherit (finalAttrs) pname version src;
    fetcherVersion = 2;
    hash = "sha256-BgYhO4ebpfPxQE3g8tLwYO/45iV0HmbBzYAAK9zHBRY=";
  };

  buildPhase = ''
    runHook preBuild
    pnpm build
    runHook postBuild
  '';

  installPhase = ''
    runHook preInstall

    mkdir -p $out/bin
    cp -r node_modules $out/
    mv build/index.js $out/bin/o3-search-mcp
    substituteInPlace $out/bin/o3-search-mcp \
      --replace-fail "/usr/bin/env node" "${lib.getExe nodejs}"
    chmod +x $out/bin/o3-search-mcp

    runHook postInstall
  '';

  meta = with lib; {
    description = "MCP server for OpenAI o3 web search";
    homepage = "https://github.com/nacyot/o3-search-mcp";
    license = licenses.mit;
    maintainers = with maintainers; [ sudosubin ];
    platforms = platforms.unix;
    mainProgram = "o3-search-mcp";
  };
})
