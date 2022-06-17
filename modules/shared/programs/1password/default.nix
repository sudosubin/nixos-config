{ config, pkgs, lib, ... }:

{
  home.packages = with pkgs; [
    _1password
  ];
}
