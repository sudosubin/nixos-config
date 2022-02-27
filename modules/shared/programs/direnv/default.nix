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
      whitelist.prefix = [ "${config.home.homeDirectory}/Code" ];
    };
  };
}
