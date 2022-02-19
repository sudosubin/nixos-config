{ config, pkgs, ... }:

{
  # Darwin network configurations
  networking = {
    dns = [ "1.1.1.1" "1.0.0.1" ];
    knownNetworkServices = [ "Thunderbolt Bridge" "USB 10/100/1000 LAN" "Wi-Fi" ];
  };

  nix = {
    extraOptions = ''
      experimental-features = nix-command flakes
    '';
    useDaemon = true;
  };

  programs.zsh.enable = true;

  environment = {
    shells = [ pkgs.zsh ];
    loginShell = "${pkgs.zsh}/bin/zsh -l";
    variables = {
      SHELL = "${pkgs.zsh}/bin/zsh";
    };
  };

  users.users."subin.kim" = {
    shell = pkgs.zsh;
    home = "/Users/subin.kim";
  };
}
