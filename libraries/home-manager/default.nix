{
  inputs,
  lib,
  pkgs,
  ...
}:

let
  inherit (pkgs.stdenvNoCC.hostPlatform) isDarwin isLinux;

in
{
  home-manager.sharedModules = [
    # sops-nix (nix flake input)
    inputs.sops-nix.homeManagerModules.sops
    # Compatibility until sops-nix stops requiring the removed Go 1.25 builder.
    {
      sops.package =
        (pkgs.callPackage inputs.sops-nix {
          pkgs = pkgs.extend (
            _: prev: {
              buildGo125Module = prev.buildGo126Module;
            }
          );
        }).sops-install-secrets;
    }

    # accounts (local)
    ./accounts/gh

    # local programs (local)
    ./programs/1password
    ./programs/act
    ./programs/agent-browser
    ./programs/agent-slack
    ./programs/caffeinate
    ./programs/cleanshot
    ./programs/clop
    ./programs/figma-agent
    ./programs/hammerspoon
    ./programs/homerow
    ./programs/music-decoy
    ./programs/orbstack
    ./programs/pi
    ./programs/redisinsight
    ./programs/sqlit
    ./programs/wifi-unredactor

    # os systems
    (lib.mkIf isDarwin ./systems/darwin)
    (lib.mkIf isLinux ./systems/linux)
  ];
}
