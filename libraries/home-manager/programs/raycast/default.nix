{ config, pkgs, lib, ... }:
with lib;

let
  cfg = config.programs.raycast;

in
{
  options.programs.raycast = {
    enable = mkEnableOption "raycast";

    package = mkOption {
      type = types.package;
      default = pkgs.raycast;
      description = "A raycast package.";
    };
  };

  config = mkIf cfg.enable {
    home.packages = [ cfg.package ];
  };
}
