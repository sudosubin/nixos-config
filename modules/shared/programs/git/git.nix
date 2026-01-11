{ config, pkgs, ... }:

{
  programs.git = {
    enable = true;
    signing = {
      key = "68971E6A5D6DE3D6";
      signByDefault = true;
    };
    ignores = [
      ".DS_Store"
      ".direnv"
      ".envrc"
      ".linear.toml"
      ".spr.yml"
      "*.pem"
    ];
    settings = {
      branch.sort = "-committerdate";
      credential.helper = "";
      credential."https://github.com".helper = "!gh auth git-credential";
      fetch = {
        all = true;
        prune = true;
        pruneTags = true;
      };
      init.defaultBranch = "main";
      push.autoSetupRemote = true;
      tag.sort = "version:refname";
      user = {
        name = "sudosubin";
        email = "sudosubin@gmail.com";
      };

    };
  };
}
