/*
  * Make nixos, nix-darwin nix configuration compatible
  * nixos: https://github.com/NixOS/nixpkgs/blob/master/nixos/modules/services/misc/nix-daemon.nix
  * nix-darwin: https://github.com/LnL7/nix-darwin/blob/master/modules/nix/default.nix
*/

{ config, lib, inputs, ... }:
with lib;

let
  inherit (inputs) darwin nixpkgs;
  cfg = config.nix;

in
{
  options = {
    nix.settings = mkOption {
      type = types.submodule {
        options = {
          auto-optimise-store = mkOption {
            type = types.bool;
            default = false;
            example = true;
          };

          substituters = mkOption {
            type = types.listOf types.str;
            example = [ https://cache.nixos.org ];
          };

          trusted-public-keys = mkOption {
            type = types.listOf types.str;
            example = [ "cache.nixos.org-1:6NCHdD59X431o0gWypbMrAURkbJ16ZPMQFGspcDShjY=" ];
          };
        };
      };
    };
  };

  config = {
    nix.binaryCaches = lib.mkIf (cfg.settings ? substituters) cfg.settings.substituters;
    nix.binaryCachePublicKeys = lib.mkIf (cfg.settings ? trusted-public-keys) cfg.settings.trusted-public-keys;
    nix.extraOptions = lib.mkIf (cfg.settings ? auto-optimise-store) ''
      auto-optimise-store = ${boolToString cfg.settings.auto-optimise-store}
    '';
  };
}
