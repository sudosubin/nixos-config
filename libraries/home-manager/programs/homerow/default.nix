{
  config,
  pkgs,
  lib,
  ...
}:
with lib;

let
  inherit (pkgs.stdenvNoCC.hostPlatform) isDarwin;
  cfg = config.services.homerow;

in
{
  options.services.homerow = {
    enable = mkEnableOption "homerow";

    package = mkPackageOption pkgs "homerow" { };

    config = {
      auto-deactivate-scrolling = mkOption {
        type = types.bool;
        default = false;
        description = "Automatic scroll deactivation";
      };
      auto-deactivate-scrolling-delay-s = mkOption {
        type = types.oneOf [
          types.int
          types.float
        ];
        default = 1;
        description = "Deactivation delay";
      };
      auto-switch-input-source-id = mkOption {
        type = types.str;
        default = "com.apple.keylayout.ABC";
        description = "Input source";
      };
      check-for-updates-automatically = mkOption {
        type = types.bool;
        default = true;
        description = "Check for updates automatically";
      };
      dash-speed-multiplier = mkOption {
        type = types.oneOf [
          types.int
          types.float
        ];
        default = 1.5;
        description = "Dash speed";
      };
      disabled-bundle-paths = mkOption {
        type = types.listOf (
          types.oneOf [
            types.path
            types.str
          ]
        );
        default = [ ];
        description = "Ignored applications";
        apply =
          value:
          if !(isList value) then
            value
          else
            "(${(strings.concatStringsSep "," (map (val: "\"${val}\"") value))})";
      };
      enable-hyper-key = mkOption {
        type = types.bool;
        default = false;
        description = "Hyperkey enabled";
      };
      hide-labels-when-nothing-is-searched = mkOption {
        type = types.bool;
        default = false;
        description = "Hide labels before search";
      };
      is-auto-click-enabled = mkOption {
        type = types.bool;
        default = true;
        description = "Automatic click";
      };
      is-scroll-shortcuts-enabled = mkOption {
        type = types.bool;
        default = true;
        description = "Scroll commands";
      };
      label-characters = mkOption {
        type = types.str;
        default = "";
        description = "Label characters";
      };
      label-font-size = mkOption {
        type = types.int;
        default = 10;
        description = "Label size";
      };
      launch-at-login = mkOption {
        type = types.bool;
        default = false;
        description = "Launch on login";
      };
      map-arrow-keys-to-scroll = mkOption {
        type = types.bool;
        default = false;
        description = "Arrow keys";
      };
      non-search-shortcut = mkOption {
        type = types.str;
        default = "⌥⌘Space"; # ⌥⌘Space
        description = "Shortcut";
      };
      scroll-keys = mkOption {
        type = types.str;
        default = "HJKL";
        description = "Scroll keys";
      };
      scroll-px-per-ms = mkOption {
        type = types.oneOf [
          types.int
          types.float
        ];
        default = 1;
        description = "Scroll speed";
      };
      scroll-shortcut = mkOption {
        type = types.str;
        default = "⇧⌘J"; # ⇧⌘J
        description = "Shortcut (Scrolling)";
      };
      scroll-show-numbers = mkOption {
        type = types.bool;
        default = true;
        description = "Show scroll area numbers";
      };
      search-shortcut = mkOption {
        type = types.str;
        default = "";
        description = "Search Shortcut";
      };
      show-menubar-icon = mkOption {
        type = types.bool;
        default = true;
        description = "Show menubar icon";
      };
      theme-id = mkOption {
        type = types.str;
        default = "original";
        description = "Theme";
      };
      use-search-predicate = mkOption {
        type = types.bool;
        default = true;
        description = "Browser labels";
      };
    };
  };

  config = mkMerge [
    {
      assertions = [
        {
          assertion = cfg.enable -> isDarwin;
          message = "Nix homerow only supports darwin.";
        }
      ];
    }

    (mkIf cfg.enable {
      home.packages = [ cfg.package ];

      darwin.defaults."com.superultra.Homerow" = cfg.config // {
        "NSStatusItem Visible Item-0" = cfg.config.show-menubar-icon;
      };

      launchd.agents.homerow = {
        enable = true;
        config = {
          ProgramArguments = [
            "${config.home.homeDirectory}/Applications/Home Manager Apps/${cfg.package.sourceRoot}/Contents/MacOS/Homerow"
          ];
          KeepAlive = true;
          ProcessType = "Interactive";
          StandardOutPath = "${config.xdg.cacheHome}/homerow.log";
          StandardErrorPath = "${config.xdg.cacheHome}/homerow.log";
        };
      };
    })
  ];
}
