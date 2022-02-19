{ config, pkgs, ... }:

{
  nix = {
    extraOptions = ''
      experimental-features = nix-command flakes
    '';
    useDaemon = true;
  };

  programs.zsh.enable = true;
  environment.loginShell = pkgs.zsh;

  users.users."subin.kim" = {
    shell = pkgs.zsh;
    home = "/Users/subin.kim";
  };
}
