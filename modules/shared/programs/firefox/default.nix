{
  config,
  pkgs,
  lib,
  ...
}:

{
  programs.firefox = {
    enable = true;
    package = pkgs.firefox;

    policies = {
      DisableFirefoxAccounts = true;
      DisableFirefoxScreenshots = true;
      DisableFirefoxStudies = true;
      DisableTelemetry = true;
      DisplayBookmarksToolbar = "newtab";
      DisplayMenuBar = "never";
      DisablePocket = true;
      EnableTrackingProtection = {
        Value = true;
        Locked = true;
        Cryptomining = true;
        Fingerprinting = true;
        EmailTracking = true;
      };
      SearchBar = "unified";
    };

    profiles.default = {
      containersForce = true;
      containers = {
        "sudosubin@gmail.com" = {
          id = 1;
          color = "blue";
          icon = "fingerprint";
        };
        "elvin@daangn.com" = {
          id = 2;
          color = "orange";
          icon = "briefcase";
        };
        "elvin@daangn.com (secondary)" = {
          id = 3;
          color = "red";
          icon = "briefcase";
        };
        "sudosubin@python.or.kr" = {
          id = 4;
          color = "blue";
          icon = "chill";
        };
        "ausg.awskrug@gmail.com" = {
          id = 5;
          color = "purple";
          icon = "food";
        };
        "sipe.team@gmail.com" = {
          id = 6;
          color = "green";
          icon = "tree";
        };
        "gdg.campuskorea@gmail.com" = {
          id = 7;
          color = "red";
          icon = "gift";
        };
      };
      extensions = {
        force = true;
        packages = with pkgs.firefox-addons; [
          multi-account-containers
          onepassword-password-manager
          ublock-origin
        ];
        settings = with pkgs.firefox-addons; {
          "${ublock-origin.addonId}" = {
            settings = {
              force = true;
              selectedFilterLists = [
                "ublock-filters"
                "ublock-badware"
                "ublock-privacy"
                "ublock-quick-fixes"
                "ublock-unbreak"
                "easylist"
                "adguard-generic"
                "adguard-spyware"
                "adguard-spyware-url"
                "adguard-cookies"
                "ublock-cookies-adguard"
                "KOR-1"
              ];
            };
          };
        };
      };
      search = {
        default = "google";
        order = [ "google" ];
        engines = {
          bing.metaData.hidden = true;
          ddg.metaData.hidden = true;
          wikipedia.metaData.hidden = true;
        };
      };
      settings = {
        "browser.search.suggest.enabled" = false;
        "browser.uiCustomization.state" = builtins.toJSON {
          "placements" = {
            "widget-overflow-fixed-list" = [ ];
            "unified-extensions-area" = [ ];
            "nav-bar" = [
              "back-button"
              "forward-button"
              "stop-reload-button"
              "vertical-spacer"
              "urlbar-container"
              "save-to-pocket-button"
              "downloads-button"
              "fxa-toolbar-menu-button"
              "ublock0_raymondhill_net-browser-action"
              "_d634138d-c276-4fc8-924b-40a0ea21d284_-browser-action"
              "unified-extensions-button"
              "_testpilot-containers-browser-action"
            ];
            "TabsToolbar" = [
              "tabbrowser-tabs"
              "new-tab-button"
              "alltabs-button"
              "firefox-view-button"
            ];
            "vertical-tabs" = [ ];
            "PersonalToolbar" = [ ];
          };
          "seen" = [ ];
          "dirtyAreaCache" = [
            "nav-bar"
            "vertical-tabs"
            "PersonalToolbar"
            "TabsToolbar"
            "unified-extensions-area"
          ];
          "currentVersion" = 22;
          "newElementCount" = 8;
        };
        "extensions.autoDisableScopes" = 0;
        "extensions.update.autoUpdateDefault" = false;
        "extensions.update.enabled" = false;
      };
    };
  };
}
