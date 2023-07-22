{ config, lib, pkgs, ... }:

{
  # Add `k` alias for `kubectl`
  home.packages = with pkgs; [
    (kubectl.overrideAttrs (attrs: {
      postInstall = ''
        ${attrs.postInstall or ""}
        install -D _output/local/go/bin/kubectl $out/bin/k
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
