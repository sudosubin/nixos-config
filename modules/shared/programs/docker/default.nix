{ config, pkgs, lib, ... }:

let
  inherit (pkgs.stdenvNoCC.hostPlatform) isDarwin;

in
{
  home.packages = with pkgs; [
    docker
    docker-compose
  ] ++ lib.optionals isDarwin [ colima ];
}
