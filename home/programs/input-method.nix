{ config, pkgs, ... }:

{
  home.packages = with pkgs; [
    kime
  ];

  i18n.inputMethod = {
    enabled = "kime";
  };
}
