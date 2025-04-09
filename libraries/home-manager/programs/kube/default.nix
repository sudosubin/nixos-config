{
  config,
  lib,
  pkgs,
  ...
}:
with lib;

let
  cfg = config.programs.kube;

  package = pkgs.kubectl.overrideAttrs (attrs: {
    postInstall = ''
      ${attrs.postInstall or ""}

      ${optionalString cfg.kAlias ''
        install -D $out/bin/kubectl $out/bin/k

        installShellCompletion --cmd k \
          --bash <($out/bin/k completion bash | sed "s/kubectl/k/g") \
          --fish <($out/bin/k completion fish | sed "s/kubectl/k/g") \
          --zsh <($out/bin/k completion zsh | sed "s/kubectl/k/g")
      ''}
    '';
  });

in
{
  options.programs.kube = {
    enable = mkEnableOption "kube";

    config = mkOption {
      type = types.nullOr types.path;
      default = null;
      defaultText = "~/.kube/config";
      apply = toString;
      description = ''
        The location of kubectl config file.
      '';
    };

    kAlias = mkOption {
      type = types.bool;
      default = false;
      description = ''
        Alias {command}`kube` to {command}`k`.
      '';
    };

    plugins = mkOption {
      type = types.listOf types.package;
      default = [ ];
      description = ''
        A list of plugins to use.
      '';
    };
  };

  config = mkIf cfg.enable {
    home.packages = [ package ] ++ cfg.plugins;

    home.sessionVariables = mkIf (cfg.config != null) {
      KUBECONFIG = cfg.config;
    };

    home.shellAliases = mkIf cfg.kAlias {
      k = "kubectl";
    };
  };
}
