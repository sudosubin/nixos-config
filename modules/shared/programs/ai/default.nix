{
  config,
  pkgs,
  lib,
  ...
}:

let
  inherit (pkgs.stdenvNoCC.hostPlatform) isDarwin;

in
{
  home.packages = with pkgs; [
    amp-cli
    pi-coding-agent
  ];

  programs.claude-code = {
    enable = true;

    settings = {
      includeCoAuthoredBy = false;
      env = {
        CLAUDE_CODE_IDE_SKIP_AUTO_INSTALL = "true";
        CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC = "1";
        ENABLE_TOOL_SEARCH = "true";
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

  services.claude-code-api = {
    enable = true;
    config = {
      server.port = 23701;
      mcp = {
        enabled = true;
        strict = true;
      };
      process_pool = {
        size = 5;
        min_idle = 1;
        max_idle = 5;
        idle_timeout_secs = 300;
        default_model = "claude-sonnet-4-5";
      };
    };
  };
}
