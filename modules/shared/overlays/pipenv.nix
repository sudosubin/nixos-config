final: { lib, ... }@prev:

{
  pipenv = prev.pipenv.overrideAttrs (oldAttrs: {
    postInstall = ''
      mkdir -p "$out/share/bash-completion/completions"
      _PIPENV_COMPLETE=bash_source "$out/bin/pipenv" > "$out/share/bash-completion/completions/pipenv"

      mkdir -p "$out/share/zsh/vendor-completions"
      _PIPENV_COMPLETE=zsh_source "$out/bin/pipenv" > "$out/share/zsh/vendor-completions/_pipenv"

      mkdir -p "$out/share/fish/vendor_completions.d"
      _PIPENV_COMPLETE=fish_source "$out/bin/pipenv" > "$out/share/fish/vendor_completions.d/pipenv.fish"
    '';
  });
}
