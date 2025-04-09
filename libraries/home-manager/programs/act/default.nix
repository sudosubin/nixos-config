{
  config,
  pkgs,
  lib,
  ...
}:
with lib;

let
  cfg = config.programs.act;

  formatConfig =
    config:
    attrsets.mapAttrs (
      name: value: if lib.isAttrs value then attrsets.mapAttrsToList (k: v: "${k}=${v}") value else value
    ) config;

  toConfigFile = generators.toKeyValue {
    mkKeyValue = key: value: "--${key} ${value}";
    listsAsDuplicateKeys = true;
  };

in
{
  options.programs.act = {
    enable = mkEnableOption "act";

    config = mkOption {
      type = with types; attrsOf (either str (either (listOf str) (attrsOf str)));
      default = { };
      example = {
        actor = "nektos/act";
        platform = {
          "ubuntu-latest" = "ghcr.io/catthehacker/ubuntu:act-latest";
        };
      };
      description = "Act configuration.";
    };
  };

  config = mkIf cfg.enable {
    home.packages = [ pkgs.act ];

    xdg.configFile = {
      ".actrc".text = toConfigFile (formatConfig cfg.config);
    };
  };
}
