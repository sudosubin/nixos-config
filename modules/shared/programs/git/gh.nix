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
        (mkGhAttachBrowser "chromium" "Default")
        (mkGhAttachBrowser "chromium" "Profile 1")
      ];
    };
  };

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
