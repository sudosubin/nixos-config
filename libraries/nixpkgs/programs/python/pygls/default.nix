self: { pkgs, ... }@super:

super.pygls.overrideAttrs (attrs: rec {
  version = "1.0.0";

  src = pkgs.fetchFromGitHub {
    owner = "openlawlibrary";
    repo = "pygls";
    rev = "v${version}";
    hash = "sha256-31J4+giK1RDBS52Q/Ia3Y/Zak7fp7gRVTQ7US/eFjtM=";
  };

  propagatedBuildInputs = with self; [
    lsprotocol
    typeguard
  ];
})
