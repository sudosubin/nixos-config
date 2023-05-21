{ config, pkgs, ... }:

{
  nix.useDaemon = true;

  security.pam = {
    enableSudoTouchIdAuth = true;
  };

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
    dock = {
      autohide = true;
      mineffect = "suck";
      mru-spaces = false;
      showhidden = false;
      show-recents = false;
      tilesize = 36;
      wvous-tl-corner = 1;
      wvous-bl-corner = 1;
      wvous-tr-corner = 1;
      wvous-br-corner = 1;
      persistent-apps = [
        "/System/Applications/Launchpad.app"
        "/System/Applications/System Settings.app"
        "/Applications/Google Chrome.app"
      ];
    };

    # finder configurations
    finder = {
      AppleShowAllFiles = true;
      AppleShowAllExtensions = true;
    };

    # system configurations
    NSGlobalDomain = {
      AppleShowAllFiles = true;
      AppleInterfaceStyle = null;
      AppleInterfaceStyleSwitchesAutomatically = false;
      AppleICUForce24HourTime = true;
      AppleShowAllExtensions = true;

      NSAutomaticCapitalizationEnabled = false;
      NSAutomaticDashSubstitutionEnabled = false;
      NSAutomaticPeriodSubstitutionEnabled = false;
      NSAutomaticQuoteSubstitutionEnabled = false;
      NSAutomaticSpellingCorrectionEnabled = false;

      InitialKeyRepeat = 15;
      KeyRepeat = 2;
      NSWindowResizeTime = null;
      NSAutomaticWindowAnimationsEnabled = false;
    };

    CustomUserPreferences."-g" = {
      AppleReduceDesktopTinting = 1;
    };

    CustomUserPreferences."com.apple.menuextra.clock" = {
      DateFormat = "d MMM HH:mm:ss";
      IsAnalog = 0;
      ShowDate = 1;
      ShowDayOfWeek = 0;
      ShowSeconds = 1;
    };
  };
}
