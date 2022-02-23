{ config, pkgs, lib, ... }:

let
  inherit (pkgs) stdenv;

in
{
  home.packages = with pkgs; [
    docker
    docker-compose_2
  ] ++ lib.optionals stdenv.isDarwin [ colima ];
}
