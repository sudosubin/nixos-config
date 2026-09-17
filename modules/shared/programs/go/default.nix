{ config, ... }:

{
  home.sessionVariables = {
    GOPATH = "${config.xdg.dataHome}/go";
    GOTELEMETRY = "off";
  };
}
