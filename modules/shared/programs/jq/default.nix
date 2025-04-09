{
  config,
  lib,
  pkgs,
  ...
}:

{
  programs.jq-patched = {
    enable = true;

    colors = {
      null = "0;33";
      false = "0;33";
      true = "0;33";
      numbers = "0;33";
      strings = "0;32";
      arrays = "0;37";
      objects = "0;37";
      fields = "0;31";
    };
  };
}
