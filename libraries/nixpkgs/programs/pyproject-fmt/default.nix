{
  fetchFromGitHub,
  lib,
  nix-update-script,
  python3Packages,
  rustPlatform,
  tombi,
}:

python3Packages.buildPythonPackage rec {
  pname = "pyproject-fmt";
  version = "2.24.0";
  pyproject = true;

  src = fetchFromGitHub {
    owner = "tox-dev";
    repo = "toml-fmt";
    rev = "${pname}/${version}";
    sha256 = "sha256-cOSfrBeFU1rKATYWRJkv9KS2cIhnI8KGUAMlgi9DRtA=";
  };

  sourceRoot = "${src.name}/pyproject-fmt";
  cargoRoot = "..";

  postUnpack = ''
    (cd source && python tasks/generate_readme.py pyproject-fmt)
  '';

  postPatch = ''
    cp -r ${tombi.src}/www.schemastore.org "$cargoDepsCopy/"
    cp -r ${tombi.src}/www.schemastore.tombi "$cargoDepsCopy/"

    substituteInPlace tests/test_pyproject_toml_fmt.py \
      --replace-fail "Path(sys.executable).parent" "Path(\"$out/bin\")"
  '';

  cargoDeps = rustPlatform.fetchCargoVendor {
    inherit
      pname
      version
      src
      ;
    hash = "sha256-aKSZ4yvU1JKaeEBczepzdExObqn6p2NSWM9z1Z33KmM=";
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

  # toml-fmt-common 1.3.5 does not yet respect NO_COLOR, fixed in main but unreleased
  disabledTests = [
    "test_main[format-cwd-no_check-in_place]"
    "test_main[format-absolute-no_check-in_place]"
  ];

  nativeCheckInputs = with python3Packages; [
    pytest-cov
    pytest-mock
    pytestCheckHook
  ];

  passthru.updateScript = nix-update-script {
    extraArgs = [
      "--version-regex=pyproject-fmt/(.+)"
    ];
  };

  meta = {
    description = "Format your pyproject.toml file";
    homepage = "https://github.com/tox-dev/toml-fmt/tree/main/pyproject-fmt";
    license = lib.licenses.mit;
    maintainers = with lib.maintainers; [ sudosubin ];
    mainProgram = "pyproject-fmt";
  };
}
