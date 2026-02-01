{
  fetchFromGitHub,
  lib,
  nix-update-script,
  python3Packages,
  rustPlatform,
}:

python3Packages.buildPythonPackage rec {
  pname = "pyproject-fmt";
  version = "2.12.1";
  pyproject = true;

  src = fetchFromGitHub {
    owner = "tox-dev";
    repo = "toml-fmt";
    rev = "pyproject-fmt/${version}";
    sha256 = "sha256-aEkLdIkX1L0jzhdyhSCSKHjk0Ojap1w9alSg7ENkTUk=";
  };

  sourceRoot = "${src.name}/pyproject-fmt";
  cargoRoot = "..";

  postUnpack = ''
    (cd source && python tasks/generate_readme.py pyproject-fmt)
  '';

  postPatch = ''
    substituteInPlace tests/test_pyproject_toml_fmt.py \
      --replace-fail "Path(sys.executable).parent" "Path(\"$out/bin\")"
  '';

  cargoDeps = rustPlatform.fetchCargoVendor {
    inherit
      pname
      version
      src
      ;
    hash = "sha256-/kKFt9FAkAfGodPpbtWFkYWHlCsPwTEgHV2+L5iytQ8=";
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

  passthru.updateScript = nix-update-script { };

  meta = {
    description = "Format your pyproject.toml file";
    homepage = "https://github.com/tox-dev/toml-fmt/tree/main/pyproject-fmt";
    license = lib.licenses.mit;
    maintainers = with lib.maintainers; [ sudosubin ];
    mainProgram = "pyproject-fmt";
  };
}
