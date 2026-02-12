{
  config,
  lib,
  pkgs,
  ...
}:

let
  inherit (pkgs.stdenvNoCC.hostPlatform) isDarwin;
  cfg = config.services.music-decoy;

in
{
  options.services.music-decoy = {
    enable = lib.mkEnableOption "music-decoy";

    package = lib.mkPackageOption pkgs "music-decoy" { };

    mediaAppPath = lib.mkOption {
      type = lib.types.nullOr (
        lib.types.oneOf [
          lib.types.path
          lib.types.str
        ]
      );
      default = null;
      example = "/Applications/Spotify.app";
      description = ''
        App bundle path launched by Music Decoy when the media Play key is pressed.
      '';
    };
  };

  config = lib.mkMerge [
    {
      assertions = [
        {
          assertion = cfg.enable -> isDarwin;
          message = "Nix music-decoy only supports darwin.";
        }
      ];
    }

    (lib.mkIf cfg.enable {
      home.packages = [ cfg.package ];

      targets.darwin.defaults = lib.mkIf (cfg.mediaAppPath != null) {
        "com.lowtechguys.MusicDecoy" = {
          mediaAppPath = toString cfg.mediaAppPath;
        };
      };

      launchd.agents.music-decoy = {
        enable = true;
        config = {
          ProgramArguments = [
            "${config.home.homeDirectory}/Applications/Home Manager Apps/Music Decoy.app/Contents/MacOS/Music Decoy"
          ];
          KeepAlive = true;
          RunAtLoad = true;
          ProcessType = "Interactive";
          StandardOutPath = "${config.xdg.cacheHome}/music-decoy.log";
          StandardErrorPath = "${config.xdg.cacheHome}/music-decoy.log";
        };
      };
    })
  ];
}
