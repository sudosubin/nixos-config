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
  version = "1.3.1";
  pyproject = true;

  src = fetchFromGitHub {
    owner = "tox-dev";
    repo = "toml-fmt";
    rev = "b7a4e8e0772f2a4cf82be1b624af7543363a0661";
    hash = "sha256-3hVw0m7v9c/+GPdXgvAUOa60oS1dh5PG3ItPCsfAZls=";
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
