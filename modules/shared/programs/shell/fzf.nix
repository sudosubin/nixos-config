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
      "--color=fg:-1,bg:-1,hl:${colors.brights.green}"
      "--color=fg+:${colors.brights.white},bg+:${colors.background},hl+:${colors.brights.green}"
      "--color=info:${colors.ansi.yellow},prompt:${colors.brights.green},pointer:${colors.ansi.cyan}"
      "--color=marker:${colors.ansi.cyan},spinner:${colors.ansi.yellow},header:${colors.ansi.cyan}"
    ];
    fileWidgetCommand = defaultCommand;
  };
}
