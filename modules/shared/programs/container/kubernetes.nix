{
  config,
  lib,
  pkgs,
  ...
}:

let
  inherit (pkgs.stdenvNoCC.hostPlatform) isDarwin isLinux;

in
{
  home.sessionVariables = {
    KUBECONFIG = "${config.xdg.configHome}/kube/config.yaml";
  };

  home.shellAliases = {
    k = "kubecolor";
    kubectl = "kubecolor";
  };

  home.packages = with pkgs; [
    kubectl
    kubectl-node-shell
    kubectx
  ];

  programs.kubecolor = {
    enable = true;
  };
}
