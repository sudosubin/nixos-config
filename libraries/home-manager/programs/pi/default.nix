{
  config,
  lib,
  pkgs,
  ...
}:

let
  cfg = config.programs.pi;
  defaultConfigDir = ".pi/agent";

  mkEntries =
    items: nameOf: sourceOf:
    map (item: lib.nameValuePair "${cfg.configDir}/${nameOf item}" { source = (sourceOf item); }) items;

  mkNoDuplicateAssertion =
    values: entityKind:
    let
      duplicates = lib.filter (value: lib.count (x: x == value) values > 1) (lib.unique values);
      mkMsg = value: "  - ${entityKind} `${toString value}`";
    in
    {
      assertion = duplicates == [ ];
      message = ''
        Must not have duplicate ${entityKind}s:
      ''
      + lib.concatStringsSep "\n" (map mkMsg duplicates);
    };

in
{
  options.programs.pi = {
    enable = lib.mkEnableOption "pi";

    package = lib.mkPackageOption pkgs "pi" { };

    configDir = lib.mkOption {
      type = lib.types.str;
      default = defaultConfigDir;
      example = ".config/pi/agent";
      description = ''
        The directory where pi agent files (extensions, skills, themes) are stored.
        This will be symlinked under `${config.home.homeDirectory}/<configDir>`.
      '';
    };

    environment = lib.mkOption {
      type = lib.types.attrsOf lib.types.str;
      default = { };
      example = lib.literalExpression ''
        {
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

    themes = lib.mkOption {
      type = lib.types.attrsOf (
        lib.types.submodule {
          options = {
            src = lib.mkOption {
              type = lib.types.path;
              description = "Path to the theme JSON file.";
            };
          };
        }
      );
      default = { };
      example = lib.literalExpression ''
        {
          dark.src = fetchurl {
            url = "https://github.com/badlogic/pi-mono/blob/v0.52.12/packages/coding-agent/src/modes/interactive/theme/dark.json";
            sha256 = "0lyh1r09fksr1rrhg4wwjlxfb8j9w5d9448d9bv5wzaqk6cjgksz";
          };
        }
      '';
      description = ''
        Custom themes to provide.
      '';
    };
  };

  config = lib.mkIf cfg.enable {
    assertions = [
      {
        assertion = !(cfg.environment ? PI_CODING_AGENT_DIR);
        message = ''
          programs.pi.environment.PI_CODING_AGENT_DIR is managed by programs.pi.configDir.
          Please set programs.pi.configDir instead of PI_CODING_AGENT_DIR.
        '';
      }
      (mkNoDuplicateAssertion (map (p: p.pname) cfg.extensions) "extension")
      (mkNoDuplicateAssertion (map (s: s.pname) cfg.skills) "skill")
    ];
    home.file = lib.listToAttrs (
      (mkEntries cfg.extensions (ext: "extensions/${ext.pname}") (x: x))
      ++ (mkEntries cfg.skills (skill: "skills/${skill.pname}") (x: x))
      ++ (mkEntries (lib.attrsToList cfg.themes) (t: "themes/${t.name}.json") (t: t.value.src))
    );
    home.packages = [ cfg.package ];
    home.sessionVariables =
      cfg.environment
      // lib.optionalAttrs (cfg.configDir != defaultConfigDir) {
        PI_CODING_AGENT_DIR = "${config.home.homeDirectory}/${cfg.configDir}";
      };
  };
}
