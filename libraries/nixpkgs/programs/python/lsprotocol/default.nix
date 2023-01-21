self: { lib, pkgs, ... }@super:

self.buildPythonPackage rec {
  pname = "lsprotocol";
  version = "2022.0.0a9";
  format = "pyproject";

  src = pkgs.fetchFromGitHub {
    owner = "microsoft";
    repo = pname;
    rev = version;
    hash = "sha256-6XecPKuBhwtkmZrGozzO+VEryI5wwy9hlvWE1oV6ajk=";
  };

  nativeBuildInputs = with self; [
    flit-core
  ];

  propagatedBuildInputs = with self; [
    cattrs
    attrs
  ];

  doCheck = false;

  pythonImportsCheck = [ "lsprotocol" ];

  meta = with lib; {
    homepage = "https://github.com/microsoft/lsprotocol";
    description = "Python implementation of the Language Server Protocol.";
    license = licenses.mit;
    maintainers = with maintainers; [ sudosubin ];
  };
}
