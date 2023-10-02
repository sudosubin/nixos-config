{ config, lib, pkgs, ... }:

{
  # Add `k` alias for `kubectl`
  home.packages = with pkgs; [
    (kubectl.overrideAttrs (attrs: {
      postInstall = ''
        ${attrs.postInstall or ""}
        install -D _output/local/go/bin/kubectl $out/bin/k

        installShellCompletion --cmd k \
          --bash <($out/bin/k completion bash | sed "s/kubectl/k/g") \
          --fish <($out/bin/k completion fish | sed "s/kubectl/k/g") \
          --zsh <($out/bin/k completion zsh | sed "s/kubectl/k/g")
      '';
    }))
    (kubectl-node-shell.overrideAttrs (attrs: {
      meta.platforms = lib.platforms.all;
    }))
  ];

  home.shellAliases = {
    k = "kubectl";
  };
}
