{
  lib,
  fetchFromGitHub,
  nix-update-script,
  python3Packages,
  makeWrapper,
  claude-code,
  codex,
  withPluginsClaude ? false,
  withPluginsCodex ? false,
  withPluginsStorage ? false,
  withPluginsMcp ? false,
  withPluginsTui ? false,
  withPluginsMetrics ? false,
}:

python3Packages.buildPythonApplication rec {
  pname = "ccproxy";
  version = "0.2.0a3";

  src = fetchFromGitHub {
    owner = "CaddyGlow";
    repo = "ccproxy-api";
    rev = "v${version}";
    hash = "sha256-ykDMf2gzJlZNswybUehscaUaWczF2lpPGZFjb6Kx2ww=";
  };

  nativeBuildInputs = lib.optionals (withPluginsClaude || withPluginsCodex) [ makeWrapper ];

  postInstall =
    lib.optionalString withPluginsClaude ''
      for bin in $out/bin/*; do
        wrapProgram $bin \
          --prefix PATH : ${lib.makeBinPath [ claude-code ]}
      done
    ''
    + lib.optionalString withPluginsCodex ''
      for bin in $out/bin/*; do
        wrapProgram $bin \
          --prefix PATH : ${lib.makeBinPath [ codex ]}
      done
    '';

  pyproject = true;

  build-system = with python3Packages; [
    hatchling
    hatch-vcs
  ];

  dependencies =
    with python3Packages;
    (
      [
        aiofiles
        fastapi
        httpx
        pydantic
        pydantic-settings
        rich
        rich-toolkit
        structlog
        typer
        typing-extensions
        uvicorn
        packaging
        pyjwt
        sortedcontainers
      ]
      ++ fastapi.optional-dependencies.standard
      ++ httpx.optional-dependencies.http2
      ++ lib.optionals withPluginsClaude optional-dependencies.plugins-claude
      ++ lib.optionals withPluginsCodex optional-dependencies.plugins-codex
      ++ lib.optionals withPluginsStorage optional-dependencies.plugins-storage
      ++ lib.optionals withPluginsMcp optional-dependencies.plugins-mcp
      ++ lib.optionals withPluginsTui optional-dependencies.plugins-tui
      ++ lib.optionals withPluginsMetrics optional-dependencies.plugins-metrics
    );

  optional-dependencies = {
    plugins-claude = with python3Packages; [
      claude-agent-sdk
      qrcode
    ];
    plugins-codex = with python3Packages; [
      pyjwt
      qrcode
    ];
    plugins-storage = with python3Packages; [
      duckdb
      duckdb-engine
      sqlalchemy
      sqlmodel
    ];
    plugins-mcp = with python3Packages; [
      fastapi-mcp
    ];
    plugins-tui = with python3Packages; [
      aioconsole
      textual
    ];
    plugins-metrics = with python3Packages; [
      prometheus-client
    ];
  };

  passthru.updateScript = nix-update-script { };

  meta = with lib; {
    description = "API server that provides an Anthropic and OpenAI compatible interface over Claude Code, allowing to use your Claude OAuth account or over the API.";
    homepage = "https://github.com/CaddyGlow/ccproxy";
    license = licenses.mit;
    maintainers = with lib.maintainers; [ sudosubin ];
    platforms = platforms.unix;
    mainProgram = "ccproxy";
  };
}
