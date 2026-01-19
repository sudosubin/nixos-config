{
  config,
  lib,
  pkgs,
  ...
}:

let
  inherit (pkgs.stdenvNoCC) isLinux;

in
{
  home.sessionVariables = {
    KUBECONFIG = "${config.xdg.configHome}/kube/config.yaml";
  };

  home.shellAliases = {
    k = "kubectl";
  };

  home.packages =
    with pkgs;
    [
      kubectl-node-shell
    ]
    ++ lib.optionals isLinux [ kubectl ];
}
