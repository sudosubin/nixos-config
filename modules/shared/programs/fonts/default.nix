{ config, pkgs, lib, ... }:

let
  inherit (pkgs.stdenvNoCC.hostPlatform) isLinux;

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

  generateFontFamily = builtins.map (family: { inherit family; });

  generateFontConfig =
    let
      toXML =
        { version ? "1.0"
        , encoding ? null
        , standalone ? null
        , dtd ? null
        }: attrset:

        let
          inherit (lib) optionalString;

          isNotNull = value: !builtins.isNull value;
          makeXmlBool = value: if value then "yes" else "no";

          repeatString = string: count:
            optionalString (count > 0) (string + (repeatString string (count - 1)));

          indent = level: repeatString " " level;

          declaration = "<?xml"
            + optionalString (isNotNull version) " version=\"${version}\""
            + optionalString (isNotNull encoding) " encoding=\"${encoding}\""
            + optionalString (isNotNull standalone) " standalone=\"${makeXmlBool standalone}\""
            + "?>";

          documentTypeDefinition = optionalString (isNotNull dtd) ("<!DOCTYPE"
            + optionalString (isNotNull dtd.rootElement) " ${dtd.rootElement}"
            + " SYSTEM"
            + optionalString (isNotNull dtd.sourceFile) " \"${dtd.sourceFile}\""
            + ">"
          );

          makeXmlContent = level: attrs: builtins.concatStringsSep "\n" (lib.mapAttrsToList
            (key: value:
              if builtins.isAttrs value then
                lib.removeSuffix "\n" ''
                  ${indent level}<${key}>
                  ${makeXmlContent (level + 2) value}
                  ${indent level}</${key}>
                ''
              else if builtins.isList value then
                lib.removeSuffix "\n" ''
                  ${indent level}<${key}>
                  ${(builtins.concatStringsSep "\n" (
                    builtins.map (item: (makeXmlContent (level + 2) item)) value
                  ))}
                  ${indent level}</${key}>
                ''
              else
                lib.removeSuffix "\n" ''
                  ${indent level}<${key}>${value}</${key}>
                ''
            )
            attrs);

          xmlContent = makeXmlContent 0 attrset;
        in
        ''
          ${declaration}
          ${documentTypeDefinition}
          ${xmlContent}
        '';
    in
    toXML {
      dtd.rootElement = "fontconfig";
      dtd.sourceFile = "urn:fontconfig:fonts.dtd";
    };

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

  gtk = lib.mkIf isLinux {
    enable = true;
    font.name = "Pretendard";
    font.size = 10;
  };

  xdg.configFile = lib.mkIf isLinux {
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
