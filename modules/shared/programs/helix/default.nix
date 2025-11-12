{
  config,
  lib,
  pkgs,
  ...
}:

{
  programs.helix = {
    enable = true;
    defaultEditor = true;
  };
}
