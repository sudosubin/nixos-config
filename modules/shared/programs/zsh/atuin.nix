{ config, pkgs, ... }:

{
  programs.atuin = {
    enable = true;
    settings = {
      auto_sync = true;
      sync_frequency = "1m";
      search_mode = "fulltext";
    };
    enableZshIntegration = false; # Use custom zsh plugin
  };
}
