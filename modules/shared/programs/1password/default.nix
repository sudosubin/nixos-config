{ config, lib, pkgs, ... }:

{
  programs._1password = {
    enable = true;
    enableFHSEnvironment = true;
  };
}
