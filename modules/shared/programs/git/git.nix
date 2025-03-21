{ config, pkgs, ... }:

{
  programs.git = {
    enable = true;
    userName = "sudosubin";
    userEmail = "sudosubin@gmail.com";
    signing = {
      key = "4BB550D927AA2762F341A86068971E6A5D6DE3D6";
      signByDefault = true;
    };
    ignores = [
      ".DS_Store"
      ".direnv"
      ".envrc"
      ".spr.yml"
      "*.pem"
    ];
    extraConfig = {
      branch.sort = "-committerdate";
      credential.helper = "";
      credential."https://github.com".helper = "!gh auth git-credential";
      init.defaultBranch = "main";
      fetch.all = true;
      fetch.prune = true;
      fetch.pruneTags = true;
      push.autoSetupRemote = true;
      tag.sort = "version:refname";
    };
  };
}
