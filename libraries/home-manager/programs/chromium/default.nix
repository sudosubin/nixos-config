/*
  * Extends home-manager's chromium module
  * https://github.com/nix-community/home-manager/blob/master/modules/programs/chromium.nix
*/

{
  config,
  lib,
  pkgs,
  ...
}:

let
  supportedBrowsers = {
    chromium = rec {
      bundleId = "org.chromium.Chromium";
      darwinDir = "Chromium";
      extensionsDir = "${darwinDir}/Home Manager Extensions";
      initialPrefsFile = "${darwinDir}/Chromium Initial Preferences";
    };
    google-chrome = rec {
      bundleId = "com.google.Chrome";
      darwinDir = "Google/Chrome";
      extensionsDir = "${darwinDir}/Home Manager Extensions";
      initialPrefsFile = "${darwinDir}/Google Chrome Initial Preferences";
    };
    google-chrome-beta = rec {
      bundleId = "com.google.Chrome.beta";
      darwinDir = "Google/Chrome Beta";
      extensionsDir = "${darwinDir}/Home Manager Extensions";
      initialPrefsFile = "${darwinDir}/Google Chrome Beta Initial Preferences";
    };
    google-chrome-dev = rec {
      bundleId = "com.google.Chrome.dev";
      darwinDir = "Google/Chrome Dev";
      extensionsDir = "${darwinDir}/Home Manager Extensions";
      initialPrefsFile = "${darwinDir}/Google Chrome Dev Initial Preferences";
    };
    brave = rec {
      bundleId = "com.brave.Browser";
      darwinDir = "BraveSoftware/Brave-Browser";
      extensionsDir = "${darwinDir}/Home Manager Extensions";
      initialPrefsFile = "${darwinDir}/Brave-Browser Initial Preferences";
    };
    vivaldi = rec {
      bundleId = "com.vivaldi.Vivaldi";
      darwinDir = "Vivaldi";
      extensionsDir = "${darwinDir}/Home Manager Extensions";
      initialPrefsFile = "${darwinDir}/Vivaldi Initial Preferences";
    };
  };

  browserModule = browser: {
    defaultOpts = lib.mkOption {
      type = lib.types.attrs;
      default = { };
      visible = pkgs.stdenv.isDarwin;
      readOnly = pkgs.stdenv.isLinux;
      description = ''
        Default chromium policy options. A list of available policies
        can be found in the Chrome Enterprise documentation:
        <https://chromeenterprise.google/policies/>
        Make sure the selected policy is supported on platform and your browser version.
      '';
    };

    initialPrefs = lib.mkOption {
      type = lib.types.attrs;
      default = { };
      visible = pkgs.stdenv.isDarwin;
      readOnly = pkgs.stdenv.isLinux;
      description = ''
        Initial preferences are used to configure the browser for the first run.
        More information can be found in the Chromium documentation:
        <https://www.chromium.org/administrators/configuring-other-preferences/>
      '';
    };

    package' = lib.mkOption {
      type = lib.types.nullOr lib.types.package;
      default = null;
      visible = pkgs.stdenv.isDarwin;
      readOnly = pkgs.stdenv.isLinux;
      description = ''
        Base package to wrap with extensions.
      '';
    };

    extensions' = lib.mkOption {
      type = lib.types.listOf lib.types.package;
      default = [ ];
      visible = pkgs.stdenv.isDarwin;
      readOnly = pkgs.stdenv.isLinux;
      description = ''
        Extension packages to copy and load via --load-extension flag.
        Extensions will be copied to ~/Library/Application Support/<browser>/Home Manager Extensions
        and only updated when version changes.
      '';
    };
  };

  browserConfig =
    browser: cfg:
    let
      hasExtensions = cfg.package' != null && cfg.extensions' != [ ];
      extensionsDir = supportedBrowsers.${browser}.extensionsDir;
      extensionPaths = map (
        ext:
        "${config.home.homeDirectory}/Library/Application Support/${extensionsDir}/${ext.id}/${ext.version}"
      ) cfg.extensions';

    in
    lib.mkIf (cfg.enable && pkgs.stdenv.isDarwin) {
      home.file = lib.mkIf (cfg.initialPrefs != { }) {
        "Library/Application Support/${supportedBrowsers.${browser}.initialPrefsFile}".text =
          builtins.toJSON cfg.initialPrefs;
      };

      targets.darwin.defaults = lib.mkIf (cfg.defaultOpts != { }) {
        "${supportedBrowsers.${browser}.bundleId}" = cfg.defaultOpts;
      };

      programs.${browser}.package = lib.mkIf hasExtensions (
        cfg.package'.overrideAttrs (attrs: {
          nativeBuildInputs = (attrs.nativeBuildInputs or [ ]) ++ [ pkgs.makeWrapper ];
          postInstall = (attrs.postInstall or "") + ''
            makeWrapper \
              "${cfg.package'}/Applications/${attrs.sourceRoot}/Contents/MacOS/${lib.strings.removeSuffix ".app" attrs.sourceRoot}" \
              "$out/Applications/${attrs.sourceRoot}/Contents/MacOS/${lib.strings.removeSuffix ".app" attrs.sourceRoot}" \
              --add-flags '--load-extension="${lib.concatStringsSep "," extensionPaths}"'
          '';
        })
      );

      home.activation = lib.mkIf hasExtensions {
        "${browser}Extensions" = lib.hm.dag.entryAfter [ "writeBoundary" ] ''
          extensionsDir="${config.home.homeDirectory}/Library/Application Support/${extensionsDir}"
          mkdir -p "$extensionsDir"

          declaredExtensions=(${
            lib.concatMapStringsSep " " (ext: ''"${ext.id}/${ext.version}"'') cfg.extensions'
          })

          for extension in "$extensionsDir"/*/*/; do
            [ -d "$extension" ] || continue
            extPath="$(basename "$(dirname "$extension")")/$(basename "$extension")"
            if [[ ! " ''${declaredExtensions[*]} " =~ " $extPath " ]]; then
              echo "Removing extension: $extPath"
              run rm -rf "$extension"
            fi
          done

          find "$extensionsDir" -mindepth 1 -maxdepth 1 -type d -empty -delete 2>/dev/null || true

          ${lib.concatMapStrings (ext: ''
            if [ ! -d "$extensionsDir/${ext.id}/${ext.version}" ]; then
              echo "Syncing extension: ${ext.id}/${ext.version}"
              run mkdir -p "$extensionsDir/${ext.id}/${ext.version}"
              run ${lib.getExe pkgs.rsync} --checksum --archive --delete --chmod=+w --no-group --no-owner "${ext}/" "$extensionsDir/${ext.id}/${ext.version}"
            fi
          '') cfg.extensions'}
        '';
      };
    };

in
{
  options.programs = lib.genAttrs (builtins.attrNames supportedBrowsers) browserModule;

  config = lib.mkMerge (
    map (browser: browserConfig browser config.programs.${browser}) (
      builtins.attrNames supportedBrowsers
    )
  );
}
