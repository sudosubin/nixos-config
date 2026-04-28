{
  config,
  lib,
  pkgs,
  ...
}:

let
  youtube-playlist-to-slack = pkgs.writeShellApplication {
    name = "youtube-playlist-to-slack";
    runtimeInputs = with pkgs; [
      agent-slack
      (python3.withPackages (
        ps: with ps; [
          google-auth
          google-auth-oauthlib
          httpx
        ]
      ))
    ];
    text = "exec python3 ${./files/youtube-playlist-to-slack.py} \"$@\"";
    meta.mainProgram = "youtube-playlist-to-slack";
  };

in
{
  home.packages = with pkgs; [
    agent-slack
    youtube-playlist-to-slack
  ];

  home.sessionVariables = {
    AGENT_SLACK_NO_UPDATE_CHECK = "1";
  };

  launchd.agents.youtube-playlist-to-slack = lib.mkIf pkgs.stdenv.isDarwin {
    enable = true;
    config = {
      ProgramArguments = [ "${lib.getExe youtube-playlist-to-slack}" ];
      EnvironmentVariables = {
        AGENT_SLACK_NO_UPDATE_CHECK = "1";
      };
      StartInterval = 600;
      RunAtLoad = true;
      StandardOutPath = "${config.xdg.cacheHome}/youtube-playlist-to-slack.log";
      StandardErrorPath = "${config.xdg.cacheHome}/youtube-playlist-to-slack.log";
    };
  };
}
