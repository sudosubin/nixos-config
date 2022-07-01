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
      # direnv
      ".envrc"
      ".direnv"
    ];
    extraConfig = {
      init.defaultBranch = "main";
      diff.age-differ = {
        textconv = "${pkgs.rage}/bin/rage -d -i ${builtins.elemAt config.secrets.identityPaths 0}";
      };
    };
  };
}
