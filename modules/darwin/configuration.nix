{ config, pkgs, ... }:

{
  nix.useDaemon = true;

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
    # dock configurations
    dock.autohide = true;
    dock.mineffect = "suck";
    dock.mru-spaces = false;
    dock.showhidden = false;
    dock.show-recents = false;
    dock.tilesize = 36;

    # finder configurations
    finder.AppleShowAllFiles = true;
    finder.AppleShowAllExtensions = true;

    # system configurations
    NSGlobalDomain.AppleShowAllFiles = true;
    NSGlobalDomain.AppleInterfaceStyle = "Dark";
    NSGlobalDomain.AppleInterfaceStyleSwitchesAutomatically = false;
    NSGlobalDomain.AppleShowAllExtensions = true;

    NSGlobalDomain.NSAutomaticCapitalizationEnabled = false;
    NSGlobalDomain.NSAutomaticDashSubstitutionEnabled = false;
    NSGlobalDomain.NSAutomaticPeriodSubstitutionEnabled = false;
    NSGlobalDomain.NSAutomaticQuoteSubstitutionEnabled = false;
    NSGlobalDomain.NSAutomaticSpellingCorrectionEnabled = false;

    NSGlobalDomain.InitialKeyRepeat = 15;
    NSGlobalDomain.KeyRepeat = 2;
    NSGlobalDomain.NSWindowResizeTime = null;
    NSGlobalDomain.NSAutomaticWindowAnimationsEnabled = false;
  };
}
