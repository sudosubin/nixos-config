{
  config,
  pkgs,
  lib,
  ...
}:
with lib;

let
  inherit (pkgs.stdenvNoCC.hostPlatform) isDarwin isLinux;
  cfg = config.programs.chromium-patched;

  package =
    if cfg.extensions != [ ] then
      (cfg.package.overrideAttrs (attrs: {
        nativeBuildInputs = (attrs.nativeBuildInputs or [ ]) ++ [ pkgs.makeWrapper ];

        postInstall =
          (attrs.postInstall or "")
          + (lib.optionalString isDarwin (
            let
              copyExtensionCommands = builtins.map (extension: ''
                cp -r "${extension}" "$out/Applications/${attrs.sourceRoot}/Contents/Extensions/${extension.id}"
              '') cfg.extensions;

              extensionPaths = builtins.map (
                extension: ''''$APP_DIR/Contents/Extensions/${extension.id}''
              ) cfg.extensions;
            in
            ''
              mkdir -p "$out/Applications/${attrs.sourceRoot}/Contents/Extensions"

              ${concatStringsSep "\n" copyExtensionCommands}

              makeWrapper \
                "${cfg.package}/Applications/${attrs.sourceRoot}/Contents/MacOS/Chromium" \
                "$out/Applications/${attrs.sourceRoot}/Contents/MacOS/Chromium" \
                --run 'export APP_DIR="$(dirname "$(dirname "$(dirname "$(realpath "''${BASH_SOURCE[0]}")")")")"' \
                --add-flags '--load-extension="${concatStringsSep "," extensionPaths}"'
            ''
          ));
      }))
    else
      cfg.package;

in
{
  options.programs.chromium-patched = {
    enable = mkEnableOption "chromium";

    package = mkPackageOption pkgs "chromium" { };

    extensions = mkOption {
      type = types.listOf types.package;
      default = [ ];
      description = "A list of extensions to load.";
    };
  };

  config = mkIf cfg.enable {
    home.packages = [ package ];
  };
}
