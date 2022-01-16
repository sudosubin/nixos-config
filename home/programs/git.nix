{ config, pkgs, ... }:

{
  home.packages = with pkgs; [
    delta
    git
  ];

  programs.git = {
    enable = true;
    userName = "sudosubin";
    userEmail = "sudosubin@gmail.com";
    signing = {
      key = "4BB550D927AA2762F341A86068971E6A5D6DE3D6";
      signByDefault = true;
    };
    ignores = [
      ".tool-versions"
      "flake.nix"
      "flake.lock"
    ];
    extraConfig = {
      init.defaultBranch = "main";
    };
  };

  programs.git.delta = {
    enable = true;
    options = {
      syntax-theme = "base16";
      file-style = "yellow ul";
      file-decoration-style = "";
      hunk-style = "syntax #08000000";
      hunk-header-decoration-style = "#08000000 ul";
      minus-style = "syntax #400000";
      minus-emph-style = "syntax #500000";
      plus-style = "syntax #003000";
      plus-emph-style = "syntax #004000";
      whitespace-error-style = "22 reverse";
      side-by-side = true;
      line-numbers-minus-style = "#08000000 #400000";
      line-numbers-zero-style = "#08000000";
      line-numbers-plus-style = "#08000000 #003000";
      line-numbers-left-style = "#08000000";
      line-numbers-right-style = "#08000000";
    };
  };
}
