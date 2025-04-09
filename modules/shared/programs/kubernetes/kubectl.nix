{
  config,
  lib,
  pkgs,
  ...
}:

{
  programs.kube = {
    enable = true;

    config = "${config.xdg.configHome}/kube/config.yaml";
    kAlias = true;

    plugins = with pkgs; [
      (kubectl-node-shell.overrideAttrs (attrs: {
        meta.platforms = lib.platforms.all;
      }))
    ];
  };
}
