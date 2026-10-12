{
  config,
  lib,
  pkgs,
  ...
}:

let
  cfg = config.services.snapzy;

  inherit (lib)
    mkEnableOption
    mkIf
    mkOption
    mkPackageOption
    ;

  settingsFormat = pkgs.formats.toml { };

  settingsFile = settingsFormat.generate "config.toml" (
    lib.recursiveUpdate {
      schema_version = 1;
      updates = {
        check_automatically = false;
        download_automatically = false;
      };
    } cfg.settings
  );
in
{
  options.services.snapzy = {
    enable = mkEnableOption "Snapzy";

    package = mkPackageOption pkgs "snapzy" { };

    # User defaults for what config.toml does not cover
    config = {
      capture = {
        includeWindowShadow = mkOption {
          type = lib.types.nullOr lib.types.bool;
          default = null;
          description = "Include the window shadow in window captures";
        };
      };

      configuration = {
        accessOnboardingPrompted = mkOption {
          type = lib.types.bool;
          default = true;
          description = "Skip the startup screen asking for access to the config file";
        };
      };

      ocr = {
        linkDetectionEnabled = mkOption {
          type = lib.types.nullOr lib.types.bool;
          default = null;
          description = "Detect links in OCR results";
        };
      };

      onboardingCompleted = mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Skip onboarding";
      };

      recording = {
        showTimeOnMenuBar = mkOption {
          type = lib.types.nullOr lib.types.bool;
          default = null;
          description = "Show the recording time in the menu bar";
        };
      };

      screenshot = {
        autoDetectElementUnderCursor = mkOption {
          type = lib.types.nullOr lib.types.bool;
          default = null;
          description = "Detect the UI element under the cursor";
        };

        autoDetectWindowUnderCursor = mkOption {
          type = lib.types.nullOr lib.types.bool;
          default = null;
          description = "Detect the window under the cursor";
        };

        livePassthrough = mkOption {
          type = lib.types.nullOr lib.types.bool;
          default = null;
          description = "Keep the screen live while selecting";
        };
      };

      splashSkipped = mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Skip the splash screen";
      };

      sponsorPromptSeen = mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Skip the sponsor prompt";
      };
    };

    settings = mkOption {
      inherit (settingsFormat) type;
      default = { };
      example = {
        general.export_location = "~/Downloads";
        capture.after.screenshot.copy_file = true;
        shortcuts.enabled = false;
      };
      description = ''
        Configuration written to {file}`$XDG_CONFIG_HOME/snapzy/config.toml`,
        which Snapzy only reads. See
        <https://github.com/duongductrong/Snapzy/blob/master/docs/CONFIGURATION.md>.
      '';
    };
  };

  config = mkIf cfg.enable {
    assertions = [
      (lib.hm.assertions.assertPlatform "services.snapzy" pkgs lib.platforms.darwin)
      {
        assertion = config.targets.darwin.copyApps.enable;
        message = "services.snapzy requires targets.darwin.copyApps.enable.";
      }
    ];

    home.packages = [ cfg.package ];

    # Link the directory, as Snapzy's atomic writes would replace a linked file
    xdg.configFile."snapzy" = {
      source = pkgs.linkFarm "snapzy-config" { "config.toml" = settingsFile; };
      onChange = ''
        domain="${config.launchd.agents.snapzy.domain}/$(id -u)"
        /bin/launchctl kickstart -k "$domain/org.nix-community.home.snapzy" \
          2>/dev/null || true
      '';
    };

    targets.darwin.defaults."com.trongduong.snapzy" = lib.filterAttrs (_: value: value != null) (
      lib.listToAttrs (
        lib.mapAttrsToListRecursive (
          path: value: lib.nameValuePair (lib.concatStringsSep "." path) value
        ) cfg.config
      )
    );

    launchd.agents.snapzy = {
      enable = true;
      config = {
        ProgramArguments = [
          "${config.home.homeDirectory}/${config.targets.darwin.copyApps.directory}/Snapzy.app/Contents/MacOS/Snapzy"
        ];
        RunAtLoad = true;
        KeepAlive = true;
        ProcessType = "Interactive";
        StandardErrorPath = "${config.home.homeDirectory}/Library/Logs/snapzy.err";
        StandardOutPath = "${config.home.homeDirectory}/Library/Logs/snapzy.log";
      };
    };
  };
}
