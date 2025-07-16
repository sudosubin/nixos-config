{
  config,
  pkgs,
  lib,
  ...
}:

{
  home.file = {
    ".claude/settings.json".text = builtins.toJSON {
      includeCoAuthoredBy = false;
      env = {
        CLAUDE_CODE_IDE_SKIP_AUTO_INSTALL = "1";
        CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC = "1";
      };
    };
  };

  home.packages = with pkgs; [
    claude-code
  ];
}
