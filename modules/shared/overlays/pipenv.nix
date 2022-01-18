final: { lib, installShellFiles, ... }@prev:

{
  pipenv = prev.pipenv.overrideAttrs (oldAttrs: {
    nativeBuildInputs = oldAttrs.nativeBuildInputs ++ [ installShellFiles ];

    postInstall = ''
      installShellCompletion --cmd pipenv \
        --bash <(_PIPENV_COMPLETE=bash_source $out/bin/pipenv) \
        --zsh <(_PIPENV_COMPLETE=zsh_source $out/bin/pipenv) \
        --fish <(_PIPENV_COMPLETE=fish_source $out/bin/pipenv)
    '';
  });
}
