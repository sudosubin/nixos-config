{
  lib,
  fetchFromGitHub,
  nix-update-script,
  python3Packages,
}:

python3Packages.buildPythonPackage rec {
  pname = "ccproxy-api";
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

  dependencies = with python3Packages; [
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
  ];

  doCheck = false;

  passthru.updateScript = nix-update-script { };

  meta = with lib; {
    description = "API server that provides an Anthropic and OpenAI compatible interface over Claude Code, allowing to use your Claude OAuth account or over the API.";
    homepage = "https://github.com/CaddyGlow/ccproxy-api";
    license = licenses.mit;
    maintainers = with lib.maintainers; [ sudosubin ];
    platforms = platforms.unix;
    mainProgram = "ccproxy-api";
  };
}
