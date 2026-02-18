{ ... }:

{
  programs.sqlit = {
    enable = true;
    configDir = ".config/sqlit";
    settings = {
      allow_plaintext_credentials = true;
      theme = "textual-ansi";
    };
  };
}
