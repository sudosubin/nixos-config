{
  config,
  lib,
  pkgs,
  ...
}:

{
  home.sessionVariables = {
    GOPATH = "${config.xdg.configHome}/go";
  };
}
