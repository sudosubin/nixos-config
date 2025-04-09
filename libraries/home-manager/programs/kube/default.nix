{
  config,
  lib,
  pkgs,
  ...
}:

let
  cfg = config.programs.kube;

  package = pkgs.kubectl.overrideAttrs (attrs: {
    postInstall = ''
      ${attrs.postInstall or ""}

      ${lib.optionalString cfg.kAlias ''
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
    enable = lib.mkEnableOption "kube";

    config = lib.mkOption {
      type = lib.types.nullOr lib.types.path;
      default = null;
      defaultText = "~/.kube/config";
      apply = toString;
      description = ''
        The location of kubectl config file.
      '';
    };

    kAlias = lib.mkOption {
      type = lib.types.bool;
      default = false;
      description = ''
        Alias {command}`kube` to {command}`k`.
      '';
    };

    plugins = lib.mkOption {
      type = lib.types.listOf lib.types.package;
      default = [ ];
      description = ''
        A list of plugins to use.
      '';
    };
  };

  config = lib.mkIf cfg.enable {
    home.packages = [ package ] ++ cfg.plugins;

    home.sessionVariables = lib.mkIf (cfg.config != null) {
      KUBECONFIG = cfg.config;
    };

    home.shellAliases = lib.mkIf cfg.kAlias {
      k = "kubectl";
    };
  };
}
