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

  package = pkgs.lsd.overrideAttrs (attrs: {
    nativeBuildInputs = (attrs.nativeBuildInputs or [ ]) ++ [ pkgs.makeWrapper ];

    postInstall = ''
      ${attrs.postInstall or ""}

      wrapProgram $out/bin/lsd \
        --prefix LS_COLORS : "${builtins.concatStringsSep ":" (mapLsColors cfg.lscolors)}"
    '';
  });
in
{
  options.programs.lsd = {
    enablePatch = mkEnableOption "lsd";

    lscolors = mkOption {
      type = types.attrsOf types.str;
      default = { };
      description = "LS_COLORS key-value attrset.";
    };
  };

  config = mkIf cfg.enablePatch {
    home.packages = [ package ];

    programs.lsd =
      mkIf (cfg.colors != { }) { settings.color.theme = "custom"; };

    xdg.configFile = {
      "lsd/colors.yaml" = mkIf (cfg.colors != { }) {
        source = yamlFormat.generate "lsd-colors" cfg.colors;
      };

      "lsd/config.yaml" = mkIf (cfg.settings != { }) {
        source = yamlFormat.generate "lsd-config" cfg.settings;
      };
    };
  };
}
