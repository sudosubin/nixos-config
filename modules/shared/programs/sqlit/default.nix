{ pkgs, ... }:

{
  home.packages = [ pkgs.sqlitx ];

  programs.sqlit = {
    enable = true;
    configDir = ".config/sqlit";
    settings = {
      allow_plaintext_credentials = true;
      process_worker = false;
      process_worker_warm_on_idle = false;
      theme = "textual-ansi";
    };
  };
}
