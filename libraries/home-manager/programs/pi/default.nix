{
  config,
  lib,
  pkgs,
  ...
}:

let
  cfg = config.programs.pi;
  defaultConfigDir = ".pi/agent";
  jsonFormat = pkgs.formats.json { };

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

    keybindings = lib.mkOption {
      type = with lib.types; nullOr (attrsOf (either str (listOf str)));
      default = null;
      example = lib.literalExpression ''
        {
          "tui.input.newLine" = [ "shift+enter" "ctrl+j" ];
          "app.model.select" = "ctrl+m";
          "app.tools.expand" = "ctrl+e";
        }
      '';
      description = ''
        Declarative contents of pi's `keybindings.json`.
        Values must be either a single key string or a list of key strings.
      '';
    };

    settings = lib.mkOption {
      type = jsonFormat.type;
      default = { };
      example = lib.literalExpression ''
        {
          collapseChangelog = true;
          theme = "github-dark";
        }
      '';
      description = ''
        Key-value settings to enforce in pi's `settings.json`.

        During activation, declared keys are merged onto the existing
        `settings.json` so runtime-modified keys not declared here are preserved.
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
        assertion = !(lib.hasPrefix "/" cfg.configDir);
        message = "programs.pi.configDir must be a path relative to HOME (e.g. .config/pi/agent).";
      }
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
      ++ lib.optional (cfg.keybindings != null) (
        lib.nameValuePair "${cfg.configDir}/keybindings.json" {
          source = jsonFormat.generate "pi-keybindings.json" cfg.keybindings;
        }
      )
    );

    home.packages = [ cfg.package ];

    home.activation = lib.mkIf (cfg.settings != { }) {
      piSettingsActivation =
        let
          configPath = "${config.home.homeDirectory}/${cfg.configDir}/settings.json";
          newConfig = jsonFormat.generate "pi-settings.json" cfg.settings;
          jq = lib.getExe pkgs.jq;
        in
        lib.hm.dag.entryAfter [ "linkGeneration" ] ''
          mkdir -p "$(dirname ${lib.escapeShellArg configPath})"
          touch ${lib.escapeShellArg configPath}
          if ! ${jq} -e . ${lib.escapeShellArg configPath} >/dev/null 2>&1; then
            printf '%s\n' '{}' > ${lib.escapeShellArg configPath}
          fi

          config="$(${jq} -s '.[0] * .[1]' ${lib.escapeShellArg configPath} ${lib.escapeShellArg newConfig})"
          printf '%s\n' "$config" > ${lib.escapeShellArg configPath}
          unset config
        '';
    };

    home.sessionVariables =
      cfg.environment
      // lib.optionalAttrs (cfg.configDir != defaultConfigDir) {
        PI_CODING_AGENT_DIR = "${config.home.homeDirectory}/${cfg.configDir}";
      };
  };
}
