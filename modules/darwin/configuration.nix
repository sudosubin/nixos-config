{ config, pkgs, ... }:

{
  nix.useDaemon = true;

  security.pam = {
    enableSudoTouchIdAuth = true;
  };

  programs.bash.enable = true;

  users.users."subin.kim" = {
    shell = pkgs.bash;
    home = "/Users/subin.kim";
  };

  environment = {
    shells = [ pkgs.bash ];
    loginShell = "${pkgs.bash}/bin/bash -l";
    pathsToLink = [ "/share/qemu" ];
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
      # persistent-apps = [
      #   "/System/Applications/Launchpad.app"
      #   "/System/Applications/System Settings.app"
      #   "/Applications/Google Chrome.app"
      # ];
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
      KeyRepeat = 1;
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
