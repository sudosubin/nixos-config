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

    mcpServers = {
      gemini-cli = {
        type = "stdio";
        command = pkgs.lib.getExe pkgs.gemini-mcp-tool;
        args = [ ];
      };
    };
  };

  programs.gemini-cli = {
    enable = true;

    # https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/configuration.md
    settings = {
      general = {
        checkpointing.enabled = true;
        disableAutoUpdate = true;
        disableUpdateNag = true;
      };
      privacy = {
        usageStatisticsEnabled = false;
      };
      security = {
        auth.selectedType = "oauth-personal";
      };
      ui = {
        hideBanner = true;
        hideTips = true;
        theme = "GitHub";
      };
    };
  };
}
