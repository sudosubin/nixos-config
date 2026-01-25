/*
  * Extends home-manager's chromium module
  * https://github.com/nix-community/home-manager/blob/master/modules/programs/chromium.nix
*/

{
  config,
  pkgs,
  lib,
  ...
}:

let
  supportedBrowsers = {
    chromium = {
      bundleId = "org.chromium.Chromium";
      initialPrefsFile = "Chromium/Chromium Initial Preferences";
    };
    google-chrome = {
      bundleId = "com.google.Chrome";
      initialPrefsFile = "Google/Chrome/Google Chrome Initial Preferences";
    };
    google-chrome-beta = {
      bundleId = "com.google.Chrome.beta";
      initialPrefsFile = "Google/Chrome Beta/Google Chrome Beta Initial Preferences";
    };
    google-chrome-dev = {
      bundleId = "com.google.Chrome.dev";
      initialPrefsFile = "Google/Chrome Dev/Google Chrome Dev Initial Preferences";
    };
    brave = {
      bundleId = "com.brave.Browser";
      initialPrefsFile = "BraveSoftware/Brave-Browser/Brave-Browser Initial Preferences";
    };
    vivaldi = {
      bundleId = "com.vivaldi.Vivaldi";
      initialPrefsFile = "Vivaldi/Vivaldi Initial Preferences";
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
  };

  browserConfig =
    browser: cfg:
    lib.mkIf (cfg.enable && pkgs.stdenv.isDarwin) {
      home.file = lib.mkIf (cfg.initialPrefs != { }) {
        "Library/Application Support/${supportedBrowsers.${browser}.initialPrefsFile}".text =
          builtins.toJSON cfg.initialPrefs;
      };

      targets.darwin.defaults = lib.mkIf (cfg.defaultOpts != { }) {
        "${supportedBrowsers.${browser}.bundleId}" = cfg.defaultOpts;
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
