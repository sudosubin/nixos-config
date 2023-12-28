{ config, pkgs, ... }:

let
  yamlFormat = pkgs.formats.yaml { };

in
{
  xdg.configFile = {
    "gh/config.yml".source = yamlFormat.generate "gh-config.yml" ({
      aliases = { };
      editor = "";
      git_protocol = "https";
      prompt = "enabled";
      version = "1";
    });
  };
}
