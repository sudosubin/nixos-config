{ config, pkgs, ... }:

{
  home.packages = with pkgs; [
    docker
    docker-compose_2
  ];
}
