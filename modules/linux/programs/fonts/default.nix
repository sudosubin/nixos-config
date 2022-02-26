{ config, pkgs, lib, ... }:

let
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
      "FiraMono Nerd Font Mono"
    ];
  };

  generateFamily = builtins.map (family: { inherit family; });

  generateFontConfig = lib.generators.toXML {
    dtd.rootElement = "fontconfig";
    dtd.sourceFile = "urn:fontconfig:fonts.dtd";
  };

in
{
  imports = [
    ../../../shared/programs/fonts
  ];

  gtk = {
    enable = true;
    font.name = "Pretendard";
    font.size = 10;
  };

  xdg.configFile = {
    "fontconfig/fonts.conf".text = generateFontConfig {
      fontconfig = [
        {
          alias.family = "serif";
          alias.prefer = generateFamily font-family.serif;
        }
        {
          alias.family = "sans";
          alias.prefer = generateFamily font-family.sans-serif;
        }
        {
          alias.family = "sans-serif";
          alias.prefer = generateFamily font-family.sans-serif;
        }
        {
          alias.family = "-apple-system";
          alias.prefer = generateFamily font-family.sans-serif;
        }
        {
          alias.family = "monospace";
          alias.prefer = generateFamily font-family.monospace;
        }
      ];
    };
  };
}
