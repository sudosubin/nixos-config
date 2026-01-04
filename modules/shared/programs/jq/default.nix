{
  config,
  lib,
  pkgs,
  ...
}:

{
  programs.jq = {
    enable = true;

    colors = {
      null = "0;33";
      false = "0;33";
      true = "0;33";
      numbers = "0;33";
      strings = "0;32";
      arrays = "0;37";
      objects = "0;37";
      objectKeys = "0;31";
    };
  };
}
