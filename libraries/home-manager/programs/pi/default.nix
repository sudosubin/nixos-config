{
  config,
  lib,
  pkgs,
  ...
}:

let
  cfg = config.programs.pi;

in
{
  options.programs.pi = {
    enable = lib.mkEnableOption "pi";

    package = lib.mkPackageOption pkgs "pi" { };

    environment = lib.mkOption {
      type = lib.types.attrsOf lib.types.str;
      default = { };
      example = lib.literalExpression ''
        {
          PI_CODING_AGENT_DIR = "''${config.xdg.configHome}/pi/agent";
          PI_SKIP_VERSION_CHECK = "1";
        }
      '';
      description = "Environment variables to set for the pi program.";
    };
  };

  config = lib.mkIf cfg.enable (
    let
      finalPackage =
        if cfg.environment == { } then
          cfg.package
        else
          cfg.package.overrideAttrs (oldAttrs: {
            postFixup = ''
              ${oldAttrs.postFixup or ""}
              wrapProgram $out/lib/pi/pi \
                ${lib.concatStringsSep " " (
                  lib.mapAttrsToList (name: value: "--set '${name}' '${toString value}'") cfg.environment
                )}
            '';
          });
    in
    {
      home.packages = [ finalPackage ];
    }
  );
}
