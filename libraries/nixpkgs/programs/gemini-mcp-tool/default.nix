{
  lib,
  buildNpmPackage,
  fetchFromGitHub,
}:

buildNpmPackage rec {
  pname = "gemini-mcp-tool";
  version = "1.1.2";

  src = fetchFromGitHub {
    owner = "jamubc";
    repo = "gemini-mcp-tool";
    rev = "v${version}";
    sha256 = "sha256-HAOS62pHF5QS6mErsS/hC4+raGYBtVI5p+WA4Zl1p/E=";
  };

  npmDepsHash = "sha256-jqVKCwGu7PxW1l/+yt4ZytsQVuylAuKixMKfXJLBO8M=";

  meta = with lib; {
    description = "MCP server for Gemini CLI integration";
    homepage = "https://github.com/jamubc/gemini-mcp-tool";
    license = licenses.mit;
    maintainers = with maintainers; [ sudosubin ];
    mainProgram = "gemini-mcp";
  };
}
