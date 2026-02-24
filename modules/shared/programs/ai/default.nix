{
  config,
  pkgs,
  ...
}:

{
  home.packages = with pkgs; [
    ccusage
    (ccusage-pi.overrideAttrs (finalAttrs: {
      installPhase = finalAttrs.installPhase + ''
        wrapProgram $out/bin/ccusage-pi \
          --set PI_AGENT_DIR "${config.xdg.configHome}/pi/agent"
      '';
    }))
    grep-app-cli
  ];

  programs.agent-browser = {
    enable = true;
    enableXdgRuntimeDir = true;
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
      spinnerVerbs = {
        mode = "replace";
        verbs = [ "Working" ];
      };
    };
  };

  programs.pi = {
    enable = true;
    environment = {
      PI_SKIP_VERSION_CHECK = "1";
    };
    configDir = ".config/pi/agent";
    extensions = with pkgs.pi-extensions; [
      claude-agent-sdk-pi
      pi-cursor-agent
      pi-cwd-history
      pi-interactive-shell
      pi-review
    ];
    skills = with pkgs.skills; [
      affaan-m.everything-claude-code.golang-patterns
      anthropics.skills.skill-creator
      sudosubin.grep-app-cli.grep-app-cli
      vercel-labs.agent-browser.agent-browser
      (vercel-labs.agent-skills.react-best-practices.overrideAttrs (oldAttrs: {
        postPatch = ''
          ${oldAttrs.postPatch or ""}
          substituteInPlace SKILL.md \
            --replace-fail "name: vercel-react-best-practices" "name: react-best-practices"
        '';
      }))
    ];
    themes = {
      # toolSuccessBg = #0d1117 + #0ac74033
      # toolErrorBg = #0d1117 + #ff808033
      # customMessageBg = #0d1117 + #5cacff33
      # thinkingXxx = #484f58 + (#bc8cff00, #bc8cff33, #bc8cff66, #bc8cff99, #bc8cffcc, #bc8cffff)
      github-dark.src = ./files/pi-github-dark.json;
    };
  };
}
