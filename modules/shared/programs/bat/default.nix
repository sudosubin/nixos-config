{ config, pkgs, ... }:

{
  programs.bat = {
    enable = true;

    config = {
      theme = "GitHub";
      style = "numbers,changes,header";
      italic-text = "always";
    };
  };
}
