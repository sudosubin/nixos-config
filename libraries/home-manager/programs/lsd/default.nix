/*
  * Extends home-manager's lsd module
  * https://github.com/nix-community/home-manager/blob/master/modules/programs/lsd.nix
*/

{ config, pkgs, lib, ... }:
with lib;

let
  cfg = config.programs.lsd;

  yamlFormat = pkgs.formats.yaml { };

  mapLsColors = lsColors: attrsets.mapAttrsToList (key: value: "${key}=${value}") lsColors;

  prefix = {
    LS_COLORS = builtins.concatStringsSep ":" (mapLsColors cfg.colors);
  };

  package = pkgs.lsd.overrideAttrs (attrs: {
    nativeBuildInputs = (attrs.nativeBuildInputs or [ ]) ++ [ pkgs.makeWrapper ];

    postInstall = ''
      ${attrs.postInstall or ""}

      wrapProgram $out/bin/lsd \
        --prefix LS_COLORS : "${prefix.LS_COLORS}"
    '';
  });
in
{
  options.programs.lsd = {
    enablePatch = mkEnableOption "lsd";

    colors = mkOption {
      type = types.attrsOf types.str;
      default = { };
      description = "LS_COLORS key-value attrset.";
    };

    themes = mkOption {
      type = types.attrsOf yamlFormat.type;
      default = { };
      description = "Theme configurations.";
    };
  };

  config = mkIf cfg.enablePatch {
    home.packages = [ package ];

    xdg.configFile = mkMerge [
      (
        attrsets.mapAttrs'
          (name: theme: nameValuePair "lsd/themes/${name}.yaml" {
            source = yamlFormat.generate "lsd-themes-${name}" theme;
          })
          cfg.themes
      )
      ({
        "lsd/config.yaml" = mkIf (cfg.settings != { }) {
          source = yamlFormat.generate "lsd-config" cfg.settings;
        };
      })
    ];
  };
}
