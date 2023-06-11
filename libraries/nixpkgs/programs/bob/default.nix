final: { lib, stdenv, installShellFiles, ... }@prev:

{
  bob = prev.bob.overrideDerivation (attrs: rec {
    nativeBuildInputs = (attrs.nativeBuildInputs or [ ]) ++ [ installShellFiles ];

    postInstall = ''
      ${attrs.postInstall or ""}
      installShellCompletion --cmd bob \
        --bash <($out/bin/bob completion) \
        --zsh <($out/bin/bob completion -z)
    '';
  });
}
