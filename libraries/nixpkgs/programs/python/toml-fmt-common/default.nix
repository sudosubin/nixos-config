{
  buildPythonPackage,
  fetchFromGitHub,
  hatch-vcs,
  hatchling,
  lib,
  pytest-cov,
  pytest-mock,
  pytestCheckHook,
  pythonOlder,
  tomli,
}:

buildPythonPackage rec {
  pname = "toml-fmt-common";
  version = "1.1.0";
  pyproject = true;

  src = fetchFromGitHub {
    owner = "tox-dev";
    repo = "toml-fmt-common";
    rev = version;
    hash = "sha256-qRKSmfYRv9AwnZ5aJoXlwql3+E94UAJBx5hK9r6rtEo=";
  };

  build-system = [
    hatch-vcs
    hatchling
  ];

  dependencies = lib.optionals (pythonOlder "3.11") [
    tomli
  ];

  pythonImportsCheck = [
    "toml_fmt_common"
  ];

  nativeCheckInputs = [
    pytest-cov
    pytest-mock
    pytestCheckHook
  ];

  meta = {
    description = "Common logic to the TOML formatter.";
    homepage = "https://github.com/tox-dev/toml-fmt-common";
    license = lib.licenses.mit;
    maintainers = with lib.maintainers; [ sudosubin ];
  };
}
