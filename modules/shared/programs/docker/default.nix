{ config, pkgs, lib, ... }:

let
  inherit (pkgs.stdenvNoCC.hostPlatform) isDarwin isLinux;

in
{
  home.packages = with pkgs; [ ]
    ++ lib.optionals isDarwin [ orbstack ]
    ++ lib.optionals isLinux [ docker docker-compose ];


  home.sessionVariables = {
    DOCKER_DEFAULT_PLATFORM = "linux/amd64";
  };
}
