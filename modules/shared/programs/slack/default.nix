{
  pkgs,
  ...
}:

{
  home.packages = with pkgs; [
    agent-slack
  ];

  home.sessionVariables = {
    AGENT_SLACK_NO_UPDATE_CHECK = "1";
  };
}
