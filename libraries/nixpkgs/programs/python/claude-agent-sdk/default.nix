{
  lib,
  buildPythonPackage,
  fetchFromGitHub,
  hatchling,
  anyio,
  mcp,
  typing-extensions,
  pytest,
  pytest-asyncio,
  pytest-cov,
  mypy,
  ruff,
}:

buildPythonPackage rec {
  pname = "claude-agent-sdk";
  version = "0.1.17";
  pyproject = true;

  src = fetchFromGitHub {
    owner = "anthropics";
    repo = "claude-agent-sdk-python";
    rev = "v${version}";
    hash = "sha256-Uwp+BBO0bQja+bPrpi4RS2M2SPjHvf3fJVlSylDPJXM=";
  };

  build-system = [
    hatchling
  ];

  dependencies = [
    anyio
    mcp
    typing-extensions
  ];

  optional-dependencies = {
    dev = [
      pytest
      pytest-asyncio
      pytest-cov
      mypy
      ruff
    ]
    ++ anyio.optional-dependencies.trio;
  };

  pythonImportsCheck = [
    "claude_agent_sdk"
  ];

  nativeCheckInputs = optional-dependencies.dev;

  meta = {
    description = "Python SDK for Claude Code";
    homepage = "https://github.com/anthropics/claude-agent-sdk-python";
    license = lib.licenses.mit;
    maintainers = with lib.maintainers; [ sudosubin ];
  };
}
