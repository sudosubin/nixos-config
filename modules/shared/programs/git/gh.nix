{ pkgs, ... }:

{
  home.packages = with pkgs; [ gh ];

  programs.gh = {
    enable = true;
    extensions = with pkgs; [ gh-attach ];
    settings = {
      aliases = { };
      editor = "";
      git_protocol = "https";
      prompt = "enabled";
    };
    gitCredentialHelper.enable = false;
  };
}
