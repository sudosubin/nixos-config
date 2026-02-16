{ lib, pkgs, ... }:

let
  colors = import ../../colors.nix;

in
{
  programs.fzf = rec {
    enable = true;
    defaultCommand = "${lib.getExe pkgs.fd} --strip-cwd-prefix --exclude .git";
    defaultOptions = [
      "--color=dark"
      "--color=fg:-1,bg:-1,hl:${colors.ansi.red}"
      "--color=fg+:${colors.ansi.white},bg+:${colors.scale.gray-7},hl+:${colors.brights.red}"
      "--color=info:${colors.ansi.yellow},prompt:${colors.ansi.blue},pointer:${colors.ansi.blue}"
      "--color=marker:${colors.ansi.blue},spinner:${colors.ansi.yellow},header:${colors.ansi.blue}"
    ];
    fileWidgetCommand = defaultCommand;
  };
}
