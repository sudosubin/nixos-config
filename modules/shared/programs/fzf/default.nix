{ config, pkgs, ... }:

{
  programs.fzf = {
    enable = true;
    defaultOptions = [
      "--color=dark"
      "--color=fg:-1,bg:-1,hl:#98c379"
      "--color=fg+:#ffffff,bg+:#282c34,hl+:#98c379"
      "--color=info:#e5c07b,prompt:#98c379,pointer:#56b6c2"
      "--color=marker:#56b6c2,spinner:#e5c07b,header:#56b6c2"
    ];
  };
}
