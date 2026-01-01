{
  config,
  pkgs,
  lib,
  ...
}:

let
  always-in-container = pkgs.firefox-addons.buildFirefoxXpiAddon rec {
    pname = "always-in-container";
    version = "1.0.7";
    addonId = "{a1e9543e-5f73-4763-b376-04e53fd12cbd}";
    url = "https://addons.mozilla.org/firefox/downloads/file/4032840/always_in_container-${version}.xpi";
    sha256 = "sha256-bLxjL2P6Sd06q98MSHYRTNigtcjGwn/C2r4ANWCqKrw=";
    meta = { };
  };

  trancyfordesktop = pkgs.firefox-addons.buildFirefoxXpiAddon rec {
    pname = "trancyfordesktop";
    version = "7.7.6";
    addonId = "{29f42579-9618-4dc7-8647-eaad7cd3343e}";
    url = "https://addons.mozilla.org/firefox/downloads/file/4565802/trancyfordesktop-${version}.xpi";
    sha256 = "sha256-u1OyfFovbUNhAOSPBr3C3Zq8QK8I4jyl9zopFiPtFt0=";
    meta = { };
  };

in
{
  programs.firefox = {
    enable = true;
    package = pkgs.firefox;

    policies = {
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

    profiles.default = rec {
      containersForce = true;
      containers = {
        "sudosubin@gmail.com" = {
          id = 1;
          color = "toolbar";
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
        "awskrug.event@gmail.com" = {
          id = 8;
          color = "turquoise";
          icon = "food";
        };
        "support@yapp.co.kr" = {
          id = 9;
          color = "pink";
          icon = "pet";
        };
      };
      extensions = {
        force = true;
        packages = with pkgs.firefox-addons; [
          always-in-container
          multi-account-containers
          onepassword-password-manager
          private-grammar-checker-harper
          react-devtools
          trancyfordesktop
          ublock-origin
        ];
        settings = with pkgs.firefox-addons; {
          "${multi-account-containers.addonId}" = {
            settings = lib.listToAttrs (
              lib.lists.imap0 (i: _: {
                name = "open_container_${toString i}";
                value = "firefox-container-${toString (i + 1)}";
              }) (lib.lists.sortOn (c: c.id) (lib.attrValues containers))
            );
          };
          "${ublock-origin.addonId}" = {
            settings = {
              force = true;
              selectedFilterLists = [
                "user-filters"
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
              user-filters = lib.strings.concatLines [
                "||accounts.google.com/gsi/*$xhr,script,3p"
              ];
            };
          };
        };
      };
      search = {
        default = "google";
        force = true;
        order = [ "google" ];
        engines = {
          bing.metaData.hidden = true;
          ddg.metaData.hidden = true;
          wikipedia.metaData.hidden = true;
        };
      };
      settings = {
        "browser.toolbars.bookmarks.visibility" = "never";
        "browser.search.suggest.enabled" = false;
        "browser.uiCustomization.state" = builtins.toJSON {
          "placements" = {
            "widget-overflow-fixed-list" = [ ];
            "unified-extensions-area" = [ "_testpilot-containers-browser-action" ];
            "nav-bar" = [
              "back-button"
              "forward-button"
              "vertical-spacer"
              "stop-reload-button"
              "urlbar-container"
              "save-to-pocket-button"
              "fxa-toolbar-menu-button"
              "downloads-button"
              "ublock0_raymondhill_net-browser-action"
              "_d634138d-c276-4fc8-924b-40a0ea21d284_-browser-action"
              "unified-extensions-button"
              "alltabs-button"
            ];
            "TabsToolbar" = [
              "tabbrowser-tabs"
              "alltabs-button"
            ];
            "vertical-tabs" = [ ];
            "PersonalToolbar" = [ ];
          };
          "seen" = [ ];
          "dirtyAreaCache" = [ ];
          "currentVersion" = 22;
        };
        "browser.urlbar.decodeURLsOnCopy" = true;
        "extensions.autoDisableScopes" = 0;
        "extensions.update.autoUpdateDefault" = false;
        "extensions.update.enabled" = false;
        "gnomeTheme.activeTabContrast" = true;
        "gnomeTheme.normalWidthTabs" = true;
        "layout.spellcheckDefault" = 0;
        "svg.context-properties.content.enabled" = true;
        "toolkit.legacyUserProfileCustomizations.stylesheets" = true;
        "widget.gtk.rounded-bottom-corners.enabled" = true;
      };
      userChrome = ''
        @import "${pkgs.firefox-gnome-theme}/share/firefox-gnome-theme/userChrome.css";
        ${builtins.readFile ./files/userChrome.css}
      '';
      userContent = ''
        @import "${pkgs.firefox-gnome-theme}/share/firefox-gnome-theme/userContent.css";
      '';
    };
  };
}
