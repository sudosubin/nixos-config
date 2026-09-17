{
  config,
  lib,
  pkgs,
  ...
}:

let
  inherit (pkgs.stdenvNoCC.hostPlatform) isDarwin;
  cfg = config.programs.redisinsight;
  copyApps = config.targets.darwin.copyApps;
  appPath = "${config.home.homeDirectory}/${copyApps.directory}/Redis Insight.app";

in
{
  options.programs.redisinsight = {
    enable = lib.mkEnableOption "redisinsight";

    package = lib.mkPackageOption pkgs "redisinsight" { };

    dataDir = lib.mkOption {
      type = lib.types.nullOr lib.types.str;
      default = null;
      example = lib.literalExpression ''"''${config.xdg.dataHome}/redis-insight"'';
      description = ''
        Absolute path to relocate Redis Insight's data dir to.
        Left at `null` to use Redis Insight's own default (`~/.redis-insight`).
      '';
    };
  };

  config = lib.mkMerge [
    {
      assertions = [
        {
          assertion = cfg.enable -> isDarwin;
          message = "Nix redisinsight only supports darwin.";
        }
        {
          assertion = cfg.enable && cfg.dataDir != null -> copyApps.enable;
          message = "programs.redisinsight.dataDir requires targets.darwin.copyApps.enable: LSEnvironment injection needs a writable copy under ~/${copyApps.directory}, which copyApps provides.";
        }
      ];
    }

    (lib.mkIf cfg.enable {
      home.packages = [ cfg.package ];
    })

    (lib.mkIf (cfg.enable && cfg.dataDir != null) {
      home.activation.redisinsightDataDir = lib.hm.dag.entryAfter [ "copyApps" ] ''
        if [ -d "${appPath}" ]; then
          run /usr/bin/plutil \
            -replace LSEnvironment.RI_APP_FOLDER_ABSOLUTE_PATH -string "${cfg.dataDir}" \
            "${appPath}/Contents/Info.plist"

          run /usr/bin/codesign --force --deep --sign - "${appPath}"
        fi
      '';
    })
  ];
}
