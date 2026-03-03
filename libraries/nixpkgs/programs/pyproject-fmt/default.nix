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
  version = "2.17.0";
  pyproject = true;

  src = fetchFromGitHub {
    owner = "tox-dev";
    repo = "toml-fmt";
    rev = "${pname}/${version}";
    sha256 = "sha256-3u0LUTZetMheBVFba7G1J51JOwGk0HR1sxSv8K/+QnE=";
  };

  sourceRoot = "${src.name}/pyproject-fmt";
  cargoRoot = "..";

  postUnpack = ''
    (cd source && python tasks/generate_readme.py pyproject-fmt)

    cp -r ${tombi.src}/www.schemastore.org "$NIX_BUILD_TOP/"
    cp -r ${tombi.src}/www.schemastore.tombi "$NIX_BUILD_TOP/"
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
    hash = "sha256-/jmVehmTEElvpNeFWU5fPz6vAfLBRTX7xU36iIvOUGQ=";
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
