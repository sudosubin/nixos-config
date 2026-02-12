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
      spinnerVerbs = {
        mode = "replace";
        verbs = [ "Working" ];
      };
    };
  };

  programs.pi = {
    enable = true;
    environment = {
      PI_CODING_AGENT_DIR = "${config.xdg.configHome}/pi/agent";
      PI_SKIP_VERSION_CHECK = "1";
    };
    extensions = with pkgs.pi-extensions; [
      pi-cline-free-models
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
  };
}
