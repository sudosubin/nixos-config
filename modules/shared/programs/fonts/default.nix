{ config, pkgs, lib, ... }:

let
  inherit (pkgs) stdenv;

  font-family = {
    serif = [
      "Noto Serif CJK KR"
    ];
    sans-serif = [
      "Pretendard"
      "Noto Sans CJK KR"
      "Noto Sans CJK JP"
      "Noto Sans CJK TC"
      "Noto Sans CJK SC"
      "Noto Sans CJK HK"
    ];
    monospace = [
      "PragmataProMono Nerd Font Mono"
    ];
  };

  generateFontConfig = lib.generators.toXML {
    dtd.rootElement = "fontconfig";
    dtd.sourceFile = "urn:fontconfig:fonts.dtd";
  };

  generateFontFamily = builtins.map (family: { inherit family; });

in
{
  home.packages = with pkgs; [
    noto-fonts
    noto-fonts-cjk
    noto-fonts-emoji
    pragmatapro
    pretendard
  ];

  fonts.fontconfig = {
    enable = true;
  };

  gtk = lib.mkIf stdenv.isLinux {
    enable = true;
    font.name = "Pretendard";
    font.size = 10;
  };

  xdg.configFile = lib.mkIf stdenv.isLinux {
    "fontconfig/fonts.conf".text = generateFontConfig {
      fontconfig = [
        {
          alias.family = "serif";
          alias.prefer = generateFontFamily font-family.serif;
        }
        {
          alias.family = "sans";
          alias.prefer = generateFontFamily font-family.sans-serif;
        }
        {
          alias.family = "sans-serif";
          alias.prefer = generateFontFamily font-family.sans-serif;
        }
        {
          alias.family = "-apple-system";
          alias.prefer = generateFontFamily font-family.sans-serif;
        }
        {
          alias.family = "monospace";
          alias.prefer = generateFontFamily font-family.monospace;
        }
      ];
    };
  };
}
