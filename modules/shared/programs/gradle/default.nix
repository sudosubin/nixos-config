{ config, ... }:

{
  home.sessionVariables = {
    GRADLE_USER_HOME = "${config.xdg.dataHome}/gradle";
  };
}
