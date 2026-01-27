{ ... }:

{
  programs.atuin = {
    enable = true;
    settings = {
      auto_sync = true;
      update_check = false;
      sync_frequency = "1m";
      style = "compact";
      invert = true;
      inline_height = 9;
      show_help = false;
    };
  };
}
