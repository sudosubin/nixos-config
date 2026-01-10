{
  lib,
  python3Packages,
  fetchFromGitHub,
  nix-update-script,
  rustPlatform,
}:

python3Packages.buildPythonPackage rec {
  pname = "pyproject-fmt";
  version = "2.11.1";
  pyproject = true;

  src = fetchFromGitHub {
    owner = "tox-dev";
    repo = "toml-fmt";
    rev = "pyproject-fmt/${version}";
    sha256 = "sha256-e6fiFJst510SdqYfY7WiEusiud7xtKiXAfTwmW4+LA0=";
  };

  sourceRoot = "${src.name}/pyproject-fmt";
  cargoRoot = "..";

  postPatch = ''
    substituteInPlace tests/test_pyproject_toml_fmt.py \
      --replace-fail "Path(sys.executable).parent" "Path(\"$out/bin\")"
  '';

  cargoDeps = rustPlatform.fetchCargoVendor {
    inherit
      pname
      version
      src
      cargoRoot
      ;
    hash = "sha256-11OB0A8T6bbfsik5ivbZKtU8QISYi1hQTS0civ0ryi4=";
  };

  dependencies = with python3Packages; [
    toml-fmt-common
  ];

  env = {
    CARGO_TARGET_DIR = "./target";
  };

  pythonImportsCheck = [ "pyproject_fmt" ];

  nativeBuildInputs = [
    rustPlatform.cargoSetupHook
    rustPlatform.maturinBuildHook
  ];

  nativeCheckInputs = with python3Packages; [
    pytest-cov
    pytest-mock
    pytestCheckHook
  ];

  passthru.updateScript = ./update.sh;

  meta = {
    description = "Format your pyproject.toml file";
    homepage = "https://github.com/tox-dev/toml-fmt/tree/main/pyproject-fmt";
    license = lib.licenses.mit;
    maintainers = with lib.maintainers; [ sudosubin ];
    mainProgram = "pyproject-fmt";
  };
}
