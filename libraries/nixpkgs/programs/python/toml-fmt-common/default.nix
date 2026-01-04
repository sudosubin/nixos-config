{
  lib,
  python,
  buildPythonPackage,
  fetchFromGitHub,
  hatchling,
  hatch-vcs,
  tomli,
  pytest,
  pytest-cov,
  pytest-mock,
  pythonOlder,
  nix-update-script,
  pytestCheckHook,
}:

buildPythonPackage rec {
  pname = "toml-fmt-common";
  version = "1.0.1";
  pyproject = true;

  src = fetchFromGitHub {
    owner = "tox-dev";
    repo = "toml-fmt-common";
    rev = version;
    hash = "sha256-fV+2tOGD220kHQC6aU1sVqxmaL0cVLBjwLLkZ865BHg=";
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
