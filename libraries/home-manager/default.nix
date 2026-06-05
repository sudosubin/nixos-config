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

    # local programs (local)
    ./programs/1password
    ./programs/act
    ./programs/agent-browser
    ./programs/caffeinate
    ./programs/cleanshot
    ./programs/clop
    ./programs/figma-agent
    ./programs/hammerspoon
    ./programs/homerow
    ./programs/music-decoy
    ./programs/orbstack
    ./programs/pi
    ./programs/sqlit
    ./programs/yabai

    # os systems
    (lib.mkIf isDarwin ./systems/darwin)
    (lib.mkIf isLinux ./systems/linux)
  ];
}
