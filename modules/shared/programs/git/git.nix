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
      credential.helper = "";
      credential."https://github.com".helper = "!gh auth git-credential";
      diff.age-differ = {
        textconv = "${pkgs.rage}/bin/rage -d -i ${builtins.elemAt config.secrets.identityPaths 0}";
      };
      init.defaultBranch = "main";
    };
  };
}
