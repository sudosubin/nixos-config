{
  config,
  lib,
  pkgs,
  ...
}:

let
  cfg = config.programs.sqlit;
  defaultConfigDir = ".sqlit";
  jsonFormat = pkgs.formats.json { };

in
{
  options.programs.sqlit = {
    enable = lib.mkEnableOption "sqlit";

    package = lib.mkPackageOption pkgs "sqlit-tui" { };

    configDir = lib.mkOption {
      type = lib.types.str;
      default = defaultConfigDir;
      example = ".config/sqlit";
      description = ''
        The directory where sqlit config files (connections, settings) are stored.
        This will be symlinked under `${config.home.homeDirectory}/<configDir>`.
      '';
    };

    settings = lib.mkOption {
      type = jsonFormat.type;
      default = { };
      example = lib.literalExpression ''
        {
          theme = "tokyo-night";
        }
      '';
      description = ''
        Key-value settings to enforce in sqlit's `settings.json`.

        During activation, declared keys are merged onto the existing
        `settings.json` so runtime-modified keys not declared here are preserved.
      '';
    };
  };

  config = lib.mkIf cfg.enable {
    assertions = [
      {
        assertion = !(lib.hasPrefix "/" cfg.configDir);
        message = "programs.sqlit.configDir must be empty or a path relative to HOME (e.g. .config/sqlit).";
      }
    ];

    home.packages = [ cfg.package ];

    home.activation = lib.mkIf (cfg.settings != { }) {
      sqlitSettingsActivation =
        let
          configPath = "${config.home.homeDirectory}/${cfg.configDir}/settings.json";
          newConfig = jsonFormat.generate "sqlit-settings.json" cfg.settings;
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

    home.sessionVariables = lib.optionalAttrs (cfg.configDir != defaultConfigDir) {
      SQLIT_CONFIG_DIR = "${config.home.homeDirectory}/${cfg.configDir}";
    };
  };
}
