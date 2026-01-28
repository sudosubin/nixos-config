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

    enableWidevineCdm = lib.mkOption {
      type = lib.types.bool;
      default = false;
      visible = pkgs.stdenv.isDarwin;
      readOnly = pkgs.stdenv.isLinux;
      description = ''
        Whether to enable Widevine CDM support for DRM-protected content.
        This copies WidevineCdm from google-chrome package to chromium.
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
      hasWidevineCdm = cfg.enableWidevineCdm;
      extensionsDir = supportedBrowsers.${browser}.extensionsDir;
      extensionPaths = map (
        ext: "${config.home.homeDirectory}/Library/Application Support/${extensionsDir}/${ext.id}"
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

      programs.${browser}.package = lib.mkIf (hasExtensions || hasWidevineCdm) (
        cfg.package'.overrideAttrs (attrs: {
          nativeBuildInputs = (attrs.nativeBuildInputs or [ ]) ++ [ pkgs.makeWrapper ];
          postInstall =
            (attrs.postInstall or "")
            + (lib.optionalString hasExtensions ''
              makeWrapper \
                "${cfg.package'}/Applications/${attrs.sourceRoot}/Contents/MacOS/${lib.strings.removeSuffix ".app" attrs.sourceRoot}" \
                "$out/Applications/${attrs.sourceRoot}/Contents/MacOS/${lib.strings.removeSuffix ".app" attrs.sourceRoot}" \
                --add-flags '--load-extension="${lib.concatStringsSep "," extensionPaths}"'
            '')
            + (lib.optionalString hasWidevineCdm ''
              cp -R \
                "${pkgs.google-chrome}/Applications/Google Chrome.app/Contents/Frameworks/Google Chrome Framework.framework/Libraries/WidevineCdm" \
                "$out/Applications/${attrs.sourceRoot}/Contents/Frameworks/${lib.strings.removeSuffix ".app" attrs.sourceRoot} Framework.framework/Libraries/WidevineCdm"
            '');
        })
      );

      home.activation = lib.mkIf hasExtensions {
        "${browser}Extensions" = lib.hm.dag.entryAfter [ "writeBoundary" ] ''
          extensionsDir="${config.home.homeDirectory}/Library/Application Support/${extensionsDir}"
          mkdir -p "$extensionsDir"

          needsSync() {
            local src="$1" dst="$2"
            [ ! -f "$dst/manifest.json" ] || \
            [ "$(${lib.getExe pkgs.jq} -r '.version' "$src/manifest.json")" != "$(${lib.getExe pkgs.jq} -r '.version' "$dst/manifest.json")" ]
          }

          declaredExtensions=(${lib.concatMapStringsSep " " (ext: ''"${ext.id}"'') cfg.extensions'})

          for extension in "$extensionsDir"/*/; do
            [ -d "$extension" ] || continue
            extId=$(basename "$extension")
            if [[ ! " ''${declaredExtensions[*]} " =~ " $extId " ]]; then
              echo "Removing extension: $extId"
              run rm -rf "$extension"
            fi
          done

          ${lib.concatMapStrings (ext: ''
            if needsSync "${ext}" "$extensionsDir/${ext.id}"; then
              echo "Syncing extension: ${ext.id}"
              run ${lib.getExe pkgs.rsync} --checksum --archive --delete --chmod=+w --no-group --no-owner "${ext}/" "$extensionsDir/${ext.id}/"
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
