{ config, pkgs, ... }:

{
  imports = [
    ../darwin/programs/skhd
    ../darwin/programs/yabai
  ];

  nix = {
    useDaemon = true;
    extraOptions = ''
      experimental-features = nix-command flakes
    '';
  };

  nixpkgs.config.allowUnfree = true;
  nixpkgs.config.permittedInsecurePackages = [
    "openssl-1.0.2u"
  ];

  programs.zsh.enable = true;

  users.users."subin.kim" = {
    shell = pkgs.zsh;
    home = "/Users/subin.kim";
  };

  environment = {
    shells = [ pkgs.zsh ];
    loginShell = "${pkgs.zsh}/bin/zsh -l";
    variables = {
      SHELL = "${pkgs.zsh}/bin/zsh";
    };
  };

  system.defaults = {
    dock.autohide = true;
    NSGlobalDomain.InitialKeyRepeat = 15;
    NSGlobalDomain.KeyRepeat = 2;

    NSGlobalDomain.NSWindowResizeTime = null;
    # NSGlobalDomain.NSAutomaticWindowAnimationsEnabled = false;
  };
}
