{
  config,
  lib,
  ...
}:

let
  cfg = config.programs.pi-coding-agent;

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
    home.file = lib.mkMerge [
      (mkPackageFiles "extensions" cfg.extensions)
      (mkPackageFiles "skills" cfg.skills)
      (lib.mapAttrs' (
        name: source: lib.nameValuePair "${cfg.configDir}/themes/${name}.json" { inherit source; }
      ) cfg.themes)
    ];
  };
}
