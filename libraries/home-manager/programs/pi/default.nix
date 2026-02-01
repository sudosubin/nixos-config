{
  config,
  lib,
  pkgs,
  ...
}:

let
  cfg = config.programs.pi;
  agentDir = cfg.environment.PI_CODING_AGENT_DIR or "${config.home.homeDirectory}/.pi/agent";

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

    extensions = lib.mkOption {
      type = lib.types.listOf lib.types.package;
      default = [ ];
      example = lib.literalExpression ''
        [
          pkgs.pi-extensions.some-extension

          # Wrap a local directory
          (pkgs.runCommand "my-ext" {} '''
            cp -r ''${./my-extension} $out
          ''')

          # Wrap a single file
          (pkgs.writeText "simple-ext.ts" (builtins.readFile ./simple.ts))
        ]
      '';
      description = ''
        Pi extension packages to install.
        Each package's pname is used as the extension name in the extensions directory.
      '';
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

      extensionsDir =
        if lib.hasPrefix "${config.home.homeDirectory}/" agentDir then
          lib.removePrefix "${config.home.homeDirectory}/" agentDir + "/extensions"
        else
          throw "programs.pi: PI_CODING_AGENT_DIR must be under home directory";
    in
    {
      assertions =
        let
          pnames = map (ext: ext.pname) cfg.extensions;
          duplicates = lib.filter (p: lib.count (x: x == p) pnames > 1) (lib.unique pnames);
        in
        [
          {
            assertion = duplicates == [ ];
            message = "programs.pi.extensions: duplicate pnames found: ${lib.concatStringsSep ", " duplicates}";
          }
        ];

      home.packages = [ finalPackage ];

      home.file = lib.listToAttrs (
        map (ext: lib.nameValuePair "${extensionsDir}/${ext.pname}" { source = ext; }) cfg.extensions
      );
    }
  );
}
