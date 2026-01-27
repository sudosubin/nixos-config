{ config, ... }:

{
  home.sessionVariables = {
    GOPATH = "${config.xdg.configHome}/go";
  };
}
