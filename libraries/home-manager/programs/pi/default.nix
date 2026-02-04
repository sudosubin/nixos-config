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

    skills = lib.mkOption {
      type = lib.types.listOf lib.types.package;
      default = [ ];
      example = lib.literalExpression ''
        [
          pkgs.skills.some-skill

          # Wrap a local skill directory (must contain SKILL.md)
          (pkgs.runCommand "my-skill" {} '''
            cp -r ''${./my-skill} $out
          ''')
        ]
      '';
      description = ''
        Pi skill packages to install.
        Each package's pname is used as the skill name in the skills directory.
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

      relativeAgentDir =
        if lib.hasPrefix "${config.home.homeDirectory}/" agentDir then
          lib.removePrefix "${config.home.homeDirectory}/" agentDir
        else
          throw "programs.pi: PI_CODING_AGENT_DIR must be under home directory";

      extensionsDir = "${relativeAgentDir}/extensions";
      skillsDir = "${relativeAgentDir}/skills";
    in
    {
      assertions =
        let
          extensionPnames = map (ext: ext.pname) cfg.extensions;
          extensionDuplicates = lib.filter (p: lib.count (x: x == p) extensionPnames > 1) (
            lib.unique extensionPnames
          );
          skillPnames = map (skill: skill.pname) cfg.skills;
          skillDuplicates = lib.filter (p: lib.count (x: x == p) skillPnames > 1) (lib.unique skillPnames);
        in
        [
          {
            assertion = extensionDuplicates == [ ];
            message = "programs.pi.extensions: duplicate pnames found: ${lib.concatStringsSep ", " extensionDuplicates}";
          }
          {
            assertion = skillDuplicates == [ ];
            message = "programs.pi.skills: duplicate pnames found: ${lib.concatStringsSep ", " skillDuplicates}";
          }
        ];

      home.packages = [ finalPackage ];

      home.file =
        let
          extensionFiles = map (
            ext: lib.nameValuePair "${extensionsDir}/${ext.pname}" { source = ext; }
          ) cfg.extensions;
          skillFiles = map (
            skill: lib.nameValuePair "${skillsDir}/${skill.pname}" { source = skill; }
          ) cfg.skills;
        in
        lib.listToAttrs (extensionFiles ++ skillFiles);
    }
  );
}
