{ config, pkgs, ... }:

{
  programs.fzf = {
    enable = true;
    defaultOptions = [
      "--color=fg:-1,bg:-1,hl:#1a7f37"
      "--color=fg+:#0E1116,bg+:#ffffff,hl+:#1a7f37"
      "--color=info:#9a6700,prompt:#1a7f37,pointer:#3192aa"
      "--color=marker:#3192aa,spinner:#9a6700,header:#3192aa"
    ];
  };
}
