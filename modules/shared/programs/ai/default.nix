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
  ];

  programs.claude-code = {
    enable = true;

    settings = {
      alwaysThinkingEnabled = true;
      includeCoAuthoredBy = false;
      model = "opusplan";
      env = {
        ANTHROPIC_DEFAULT_SONNET_MODEL = "claude-sonnet-4-5-20250929[1m]";
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
}
