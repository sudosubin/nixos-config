{ config, pkgs, ... }:

let
  toml = pkgs.formats.toml { };

in
{
  programs.direnv = {
    enable = true;
    nix-direnv.enable = true;
  };

  home.sessionVariables = {
    DIRENV_LOG_FORMAT = "";
  };

  xdg.configFile = {
    "direnv/direnv.toml".source = toml.generate "direnv.toml" {
      global = {
        load_dotenv = false;
        warn_timeout = "30s";
      };
      whitelist.prefix = [ "${config.home.homeDirectory}/Code" ];
    };
  };
}
