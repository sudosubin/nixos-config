{
  config,
  lib,
  pkgs,
  ...
}:

{
  home.packages = with pkgs; [
    amp-cli
    pi-coding-agent
  ];

  home.sessionVariables = {
    PI_CODING_AGENT_DIR = "${config.xdg.configHome}/pi/agent";
  };

  programs.claude-code = {
    enable = true;
    package = pkgs.claude-code-bin;

    settings = {
      alwaysThinkingEnabled = true;
      attribution = {
        commit = "";
        pr = "";
      };
      cleanupPeriodDays = 99999;
      env = {
        ANTHROPIC_DEFAULT_SONNET_MODEL = "claude-sonnet-4-5-20250929[1m]";
        CLAUDE_BASH_MAINTAIN_PROJECT_WORKING_DIR = "1";
        CLAUDE_CODE_IDE_SKIP_AUTO_INSTALL = "true";
        CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC = "1";
        DISABLE_INSTALLATION_CHECKS = "1";
        DISABLE_TELEMETRY = "1";
        ENABLE_TOOL_SEARCH = "true";
      };
      includeCoAuthoredBy = false;
      model = "opusplan";
      permissions = {
        defaultMode = "bypassPermissions";
      };
    };

    mcpServers = {
      gemini-cli = {
        type = "stdio";
        command = lib.getExe pkgs.gemini-mcp-tool;
        args = [ ];
      };
    };
  };

  programs.gemini-cli = {
    enable = true;
    package = pkgs.gemini-cli-bin;

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
