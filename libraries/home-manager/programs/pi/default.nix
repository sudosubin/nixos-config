{
  config,
  lib,
  pkgs,
  ...
}:

let
  cfg = config.programs.pi-coding-agent;
  jsonFormat = pkgs.formats.json { };

  mkPackageFiles =
    directory: packages:
    lib.mkMerge (
      map (package: {
        "${cfg.configDir}/${directory}/${lib.getName package}".source = package;
      }) packages
    );

in
{
  options.programs.pi-coding-agent = {
    mutableSettings = lib.mkOption {
      type = lib.types.attrsOf jsonFormat.type;
      default = { };
      example = {
        collapseChangelog = true;
        theme = "github-dark";
      };
      description = ''
        Settings merged into the writable `settings.json` during activation.
        Declared keys take precedence; runtime-only settings are preserved.
        Cannot be combined with the upstream `settings` option, which creates
        a read-only settings file.
      '';
    };

    extensions = lib.mkOption {
      type = lib.types.listOf lib.types.package;
      default = [ ];
      example = lib.literalExpression ''
        with pkgs.pi-extensions; [ pi-goal pi-review ]
      '';
      description = ''
        Extension packages linked into the agent's extensions directory.
        Each package's name is used as its filename or directory name.
      '';
    };

    skills = lib.mkOption {
      type = lib.types.listOf lib.types.package;
      default = [ ];
      example = lib.literalExpression ''
        [ pkgs.agent-skills.github.hamsurang.kit.deepwiki-cli ]
      '';
      description = ''
        Skill packages linked into the agent's skills directory.
        Each package's name is used as its directory name.
      '';
    };

    themes = lib.mkOption {
      type = lib.types.attrsOf lib.types.path;
      default = { };
      example = lib.literalExpression ''
        { github-dark = ./github-dark.json; }
      '';
      description = "Theme JSON files linked by name into the agent's themes directory.";
    };
  };

  config = lib.mkIf cfg.enable {
    assertions = [
      {
        assertion = cfg.mutableSettings == { } || cfg.settings == { };
        message = "programs.pi-coding-agent.mutableSettings and settings cannot be used together.";
      }
    ];

    home.file = lib.mkMerge [
      (mkPackageFiles "extensions" cfg.extensions)
      (mkPackageFiles "skills" cfg.skills)
      (lib.mapAttrs' (
        name: source: lib.nameValuePair "${cfg.configDir}/themes/${name}.json" { inherit source; }
      ) cfg.themes)
    ];

    home.activation = lib.mkIf (cfg.mutableSettings != { }) {
      piSettingsActivation =
        let
          configPath = "${cfg.configDir}/settings.json";
          newConfig = jsonFormat.generate "pi-settings.json" cfg.mutableSettings;
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
  };
}
