{
  config,
  lib,
  pkgs,
  ...
}:

{
  home.sessionVariables = {
    TF_CLI_CONFIG_FILE = "${config.xdg.configHome}/terraform/config.tfrc";
    TFLINT_PLUGIN_DIR = "${config.xdg.configHome}/tflint";
  };

  xdg.configFile = {
    "terraform/config.tfrc".source = ./files/config.tfrc;
    "terraform/plugin-cache/.keep".text = "";
  };
}
