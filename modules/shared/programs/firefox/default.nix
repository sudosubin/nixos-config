{
  config,
  pkgs,
  lib,
  ...
}:

let
  cfg = config.programs.firefox;
  profile = "default";

in
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

    profiles."${profile}" = {
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
      };
      extensions = {
        force = true;
        packages = with pkgs.firefox-addons; [
          multi-account-containers
          onepassword-password-manager
          ublock-origin
          (buildFirefoxXpiAddon {
            pname = "always-in-container";
            version = "1.0.7";
            addonId = "{a1e9543e-5f73-4763-b376-04e53fd12cbd}";
            url = "https://addons.mozilla.org/firefox/downloads/file/4032840/always_in_container-1.0.7.xpi";
            sha256 = "sha256-bLxjL2P6Sd06q98MSHYRTNigtcjGwn/C2r4ANWCqKrw=";
            meta = { };
          })
        ];
        settings = with pkgs.firefox-addons; {
          "${multi-account-containers.addonId}" = {
            settings = {
              open_container_0 = "firefox-container-1";
              open_container_1 = "firefox-container-2";
              open_container_2 = "firefox-container-3";
              open_container_3 = "firefox-container-4";
              open_container_4 = "firefox-container-5";
              open_container_5 = "firefox-container-6";
              open_container_6 = "firefox-container-7";
            };
          };
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
        "extensions.autoDisableScopes" = 0;
        "extensions.update.autoUpdateDefault" = false;
        "extensions.update.enabled" = false;
        "gnomeTheme.activeTabContrast" = true;
        "gnomeTheme.normalWidthTabs" = true;
        "svg.context-properties.content.enabled" = true;
        "toolkit.legacyUserProfileCustomizations.stylesheets" = true;
        "widget.gtk.rounded-bottom-corners.enabled" = true;
      };
      userChrome = ''
        @import "${pkgs.firefox-gnome-theme}/userChrome.css";

        /* https://github.com/rafaelmardojai/firefox-gnome-theme/issues/464#issuecomment-1663126448 (patch: 4px -> 2px) */

        /* Tabs containers */
        #tabbrowser-tabs[orient="vertical"]:not([expanded]) .tabbrowser-tab[usercontextid] > .tab-stack > .tab-background {
          outline: none !important;
        }

        #tabbrowser-tabs[orient="vertical"] .tabbrowser-tab[usercontextid] > .tab-stack > .tab-background {
          overflow: hidden;
        }

        #tabbrowser-tabs[orient="vertical"] .tabbrowser-tab[usercontextid] > .tab-stack > .tab-background > .tab-context-line {
          display: flex !important;
          width: 6px !important;
        }

        #tabbrowser-tabs[orient="vertical"] .tabbrowser-tab[usercontextid] .tab-label-container,
        #tabbrowser-tabs[orient="horizontal"] .tabbrowser-tab[usercontextid] .tab-label-container {
          color: initial !important;
          font-weight: initial !important;
        }

        #tabbrowser-tabs[orient="horizontal"] .tabbrowser-tab[class*="identity-color-"] > .tab-stack > .tab-content {
          background-image: radial-gradient(var(--identity-tab-color) 50%, var(--identity-tab-color) 50%) !important;
          background-position: center bottom !important;
          background-size: 100% 2px !important;
          background-repeat: no-repeat;
          border-radius: 5px;
        }

        #tabbrowser-tabs[orient="horizontal"] .tabbrowser-tab[class*="identity-color-"]:not([pinned]) .tab-content::before {
          bottom: 2px !important;
        }

        /* Needs attetion tab indicator */
        #tabbrowser-tabs[orient="horizontal"] .tabbrowser-tab[class*="identity-color-"] > .tab-stack > .tab-content[attention]:not([selected="true"]),
        #tabbrowser-tabs[orient="horizontal"] .tabbrowser-tab[class*="identity-color-"] > .tab-stack > .tab-content[pinned][titlechanged]:not([selected="true"]) {
          background-image: radial-gradient(circle at 50% 100%, transparent 7px, transparent 7px, var(--identity-tab-color) 27px) !important;
          background-position: center bottom !important;
          background-size: 100% 2px !important;
        }

        #tabbrowser-tabs[orient="horizontal"] .tabbrowser-tab[class*="identity-color-"] > .tab-stack > .tab-content[attention]:not([selected="true"])::after,
        #tabbrowser-tabs[orient="horizontal"] .tabbrowser-tab[class*="identity-color-"] > .tab-stack > .tab-content[pinned][titlechanged]:not([selected="true"])::after {
          display: block;
          position: absolute;
          left: 0;
          bottom: 0;
          width: 100%;
          height: 2px;
          content: ' ';
          background-image: radial-gradient(circle at 50% 100%, var(--gnome-tabbar-tab-needs-attetion) 7px, transparent 7px) !important;
          background-position: center bottom !important;
        }
      '';
      userContent = ''
        @import "${pkgs.firefox-gnome-theme}/userContent.css";
      '';
    };
  };
}
