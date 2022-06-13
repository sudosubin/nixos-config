{ config, pkgs, lib, ... }:

let
  inherit (pkgs) stdenv;

in
{
  home.packages = with pkgs; [
    docker
    docker-compose
  ] ++ lib.optionals stdenv.isDarwin [ colima ];
}
