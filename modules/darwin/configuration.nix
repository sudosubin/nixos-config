{ config, pkgs, ... }:

{
  security.pam = {
    services.sudo_local.touchIdAuth = true;
  };

  programs.bash = {
    enable = true;
  };

  users.users.elvin = {
    shell = pkgs.bashInteractive;
    home = "/Users/elvin";
  };

  environment = {
    shells = [ pkgs.bashInteractive ];
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
      persistent-apps = [
        "/System/Applications/Launchpad.app"
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
      AppleInterfaceStyle = "Dark";
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

    WindowManager = {
      EnableStandardClickToShowDesktop = false;
    };
  };

  system.primaryUser = "elvin";

  system.stateVersion = 6;
}
