{
  lib,
  fetchPypi,
  nix-update-script,
  python3,
}:

python3.pkgs.buildPythonPackage rec {
  pname = "sweep-autocomplete";
  version = "0.1.0";
  pyproject = true;

  src = fetchPypi {
    pname = "sweep_autocomplete";
    inherit version;
    hash = "sha256-lWmNyMh2dwqiGeAX8onlZeL+ScGUJgjY+Fn3jXZPku0=";
  };

  build-system = [ python3.pkgs.setuptools ];

  dependencies = with python3.pkgs; [
    fastapi
    uvicorn
    hypercorn
    python-multipart
    loguru
    requests
    numpy
    scipy
    regex
    brotli
    pydantic
    llama-cpp-python
    huggingface-hub
  ];

  passthru.updateScript = nix-update-script { };

  pythonImportsCheck = [ "sweep_autocomplete" ];

  meta = {
    description = "Local next-edit autocomplete server powered by llama.cpp";
    homepage = "https://pypi.org/project/sweep-autocomplete/";
    license = lib.licenses.asl20;
    maintainers = with lib.maintainers; [ sudosubin ];
    platforms = lib.platforms.unix;
    mainProgram = "sweep-autocomplete";
  };
}
