{ config, pkgs, ... }:

{
  fonts.fontconfig = {
    enable = true;
  };

  home.packages = with pkgs; [
    pretendard
    (nerdfonts.override { fonts = [ "FiraMono" ]; })
  ];
}
