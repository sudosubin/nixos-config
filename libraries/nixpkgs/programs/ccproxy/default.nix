{
  lib,
  fetchFromGitHub,
  nix-update-script,
  python3Packages,
}:

python3Packages.buildPythonApplication rec {
  pname = "ccproxy";
  version = "0.2.0a2";

  src = fetchFromGitHub {
    owner = "CaddyGlow";
    repo = "ccproxy-api";
    rev = "v${version}";
    hash = "sha256-VjZ1QULvJ7Q5GGf5i3orv7XA8KbDeaSIodoDFOKBF6U=";
  };

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
