{ config, pkgs, ... }:

{
  home.packages = with pkgs; [
    gh
  ];

  programs.gh = {
    enable = true;
    settings = {
      git_protocol = "ssh";
      prompt = "enabled";
    };
    enableGitCredentialHelper = false;
  };
}
