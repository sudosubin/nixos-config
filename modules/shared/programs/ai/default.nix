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
      includeCoAuthoredBy = false;
      env = {
        CLAUDE_CODE_IDE_SKIP_AUTO_INSTALL = "1";
        CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC = "1";
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

  services.ccproxy = {
    enable = true;
    package = pkgs.ccproxy.overridePythonAttrs (old: {
      dependencies = (old.dependencies or [ ]) ++ old.optional-dependencies.plugins-claude;
    });
    config = {
      server.port = 23701;
      plugins.codex.enabled = false;
    };
  };
}
