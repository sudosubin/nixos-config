{
  config,
  pkgs,
  lib,
  ...
}:

{
  programs.claude-code = {
    enable = true;

    settings = {
      includeCoAuthoredBy = false;
      env = {
        CLAUDE_CODE_IDE_SKIP_AUTO_INSTALL = "1";
        CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC = "1";
      };
    };
  };
}
