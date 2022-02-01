{ config, pkgs, ... }:

{
  home.packages = with pkgs; [
    noto-fonts
    noto-fonts-cjk
    noto-fonts-emoji
    pretendard
    (nerdfonts.override { fonts = [ "FiraMono" ]; })
  ];

  fonts.fontconfig = {
    enable = true;
  };
}
