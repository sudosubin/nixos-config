{ config, ... }:

{
  programs.atuin = {
    enable = true;
    settings = {
      auto_sync = true;
      inline_height = 9;
      invert = true;
      logs.dir = "${config.xdg.stateHome}/atuin/logs";
      show_help = false;
      style = "compact";
      sync_frequency = "1m";
      update_check = false;
    };
  };
}
