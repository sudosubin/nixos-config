{ pkgs, ... }:

let
  yamlFormat = pkgs.formats.yaml { };

  mkGhAttachBrowser = browser: profile: { inherit browser profile; };

in
{
  home.packages = with pkgs; [ gh ];

  xdg.configFile = {
    "gh/attach.yml".source = yamlFormat.generate "gh-attach.yml" {
      browsers = [
        (mkGhAttachBrowser "firefox" "default")
      ];
    };
  };

  programs.gh = {
    enable = true;
    extensions = with pkgs; [
      gh-attach
      gh-stack
    ];
    settings = {
      aliases = { };
      editor = "";
      git_protocol = "https";
      prompt = "enabled";
    };
    gitCredentialHelper.enable = false;
  };
}
