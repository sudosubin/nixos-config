/*
  * Extends home-manager's lsd module
  * https://github.com/nix-community/home-manager/blob/master/modules/programs/lsd.nix
*/

{
  config,
  lib,
  pkgs,
  ...
}:

let
  cfg = config.programs.lsd;

  yamlFormat = pkgs.formats.yaml { };

  mapLsColors = lsColors: lib.attrsets.mapAttrsToList (key: value: "${key}=${value}") lsColors;

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
    enablePatch = lib.mkEnableOption "lsd";

    lscolors = lib.mkOption {
      type = lib.types.attrsOf lib.types.str;
      default = { };
      description = "LS_COLORS key-value attrset.";
    };
  };

  config = lib.mkIf cfg.enablePatch {
    home.packages = [ package ];

    programs.lsd = lib.mkIf (cfg.colors != { }) { settings.color.theme = "custom"; };

    xdg.configFile = {
      "lsd/colors.yaml" = lib.mkIf (cfg.colors != { }) {
        source = yamlFormat.generate "lsd-colors" cfg.colors;
      };

      "lsd/config.yaml" = lib.mkIf (cfg.settings != { }) {
        source = yamlFormat.generate "lsd-config" cfg.settings;
      };
    };
  };
}
