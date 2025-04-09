{
  config,
  pkgs,
  lib,
  ...
}:

let
  cfg = config.programs.act;

  formatConfig =
    config:
    lib.attrsets.mapAttrs (
      name: value:
      if lib.isAttrs value then lib.attrsets.mapAttrsToList (k: v: "${k}=${v}") value else value
    ) config;

  toConfigFile = lib.generators.toKeyValue {
    mkKeyValue = key: value: "--${key} ${value}";
    listsAsDuplicateKeys = true;
  };

in
{
  options.programs.act = {
    enable = lib.mkEnableOption "act";

    config = lib.mkOption {
      type = with lib.types; attrsOf (either str (either (listOf str) (attrsOf str)));
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

  config = lib.mkIf cfg.enable {
    home.packages = [ pkgs.act ];

    xdg.configFile = {
      ".actrc".text = toConfigFile (formatConfig cfg.config);
    };
  };
}
