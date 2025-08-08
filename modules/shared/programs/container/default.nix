{
  config,
  pkgs,
  lib,
  ...
}:

let
  inherit (pkgs.stdenvNoCC.hostPlatform) isDarwin isLinux;

in
{
  home.packages =
    with pkgs;
    [
      docker
      docker-compose
      docker-credential-helpers
    ]
    ++ lib.optionals isDarwin [ colima ];

  home.sessionVariables = {
    DOCKER_DEFAULT_PLATFORM = "linux/amd64";
  };
}
