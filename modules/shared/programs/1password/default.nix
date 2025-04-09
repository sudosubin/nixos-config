{
  config,
  lib,
  pkgs,
  ...
}:

{
  programs._1password = {
    enable = true;
    enableFHSEnvironment = true;
  };

  home.packages = with pkgs; [ _1password-gui ];
}
