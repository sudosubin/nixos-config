{ config, pkgs, ... }:

{
  home.packages = with pkgs; [
    bat
  ];

  programs.bat = {
    enable = true;

    config = {
      theme = "base16";
      style = "numbers,changes,header";
      italic-text = "always";
    };
  };
}
