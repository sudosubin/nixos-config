{ config, ... }:

{
  home.sessionVariables = {
    PULUMI_HOME = "${config.xdg.dataHome}/pulumi";
  };
}
