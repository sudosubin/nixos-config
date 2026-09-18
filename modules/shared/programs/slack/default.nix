{ ... }:

{
  programs.agent-slack = {
    enable = true;
    enableXdgRuntimeDir = true;
  };

  home.sessionVariables = {
    AGENT_SLACK_NO_UPDATE_CHECK = "1";
  };
}
