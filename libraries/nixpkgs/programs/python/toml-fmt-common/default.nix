{
  buildPythonPackage,
  fetchFromGitHub,
  lib,
  pytest-cov,
  pytest-mock,
  pytestCheckHook,
  pythonOlder,
  tomli,
  uv-build,
}:

buildPythonPackage rec {
  pname = "toml-fmt-common";
  version = "1.3.5";
  pyproject = true;

  src = fetchFromGitHub {
    owner = "tox-dev";
    repo = "toml-fmt";
    # pyproject-fmt 2.29.4 needs common changes newer than the 1.3.5 common tag.
    rev = "pyproject-fmt/2.29.4";
    hash = "sha256-tP5BsCkfnRyxvAZpg65qYrCLapa0HvZVlEywMURKE+s=";
  };

  sourceRoot = "${src.name}/toml-fmt-common";

  postPatch = ''
    substituteInPlace pyproject.toml \
      --replace-fail "uv-build<0.8,>=0.7.22" uv-build
  '';

  build-system = [ uv-build ];

  dependencies = lib.optionals (pythonOlder "3.11") [ tomli ];

  pythonImportsCheck = [ "toml_fmt_common" ];

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
