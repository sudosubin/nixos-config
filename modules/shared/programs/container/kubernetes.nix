{
  config,
  pkgs,
  ...
}:

let
  aws-eks-get-token-cache = pkgs.writeShellApplication {
    name = "aws-eks-get-token-cache";
    runtimeInputs = with pkgs; [
      awscli2
      coreutils
      jq
    ];
    text = builtins.readFile ./files/aws-eks-get-token-cache.sh;
    meta.mainProgram = "aws-eks-get-token-cache";
  };

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
    aws-eks-get-token-cache
    kubectl
    kubectl-node-shell
    kubectx
  ];

  programs.kubecolor = {
    enable = true;
  };
}
