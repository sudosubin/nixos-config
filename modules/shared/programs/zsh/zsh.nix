{ config, pkgs, ... }:

{
  xdg.configFile = {
    "zsh/.p10k.zsh".source = ./files/.p10k.zsh;
  };

  programs.zsh = rec {
    enable = true;
    enableCompletion = true;
    dotDir = ".config/zsh";
    autocd = true;

    history = {
      size = 1000000;
      save = 1000000;
      path = "${config.home.homeDirectory}/${dotDir}/.zsh_history";
      extended = true;
    };

    plugins = [
      {
        name = "zsh-powerlevel10k";
        src = pkgs.zsh-powerlevel10k;
        file = "share/zsh-powerlevel10k/powerlevel10k.zsh-theme";
      }
      {
        name = "zsh-fast-syntax-highlighting";
        src = pkgs.zsh-fast-syntax-highlighting;
        file = "share/zsh/site-functions/fast-syntax-highlighting.plugin.zsh";
      }
      {
        name = "zsh-autosuggestions";
        src = pkgs.zsh-autosuggestions;
        file = "share/zsh-autosuggestions/zsh-autosuggestions.zsh";
      }
      {
        name = "zsh-completions";
        src = pkgs.zsh-completions;
      }
      {
        name = "zsh-fzf";
        src = pkgs.fzf;
        file = "share/fzf/completion.zsh";
      }
      {
        name = "zsh-fzf";
        src = pkgs.fzf;
        file = "share/fzf/key-bindings.zsh";
      }
    ];

    sessionVariables = {
      # Jetbrains
      _JAVA_AWT_WM_NONREPARENTING = "1";

      # Shell
      ZSH_AUTOSUGGEST_BUFFER_MAX_SIZE = "20";
      ZSH_AUTOSUGGEST_USE_ASYNC = "true";
      ZSH_AUTOSUGGEST_MANUAL_REBIND = "true";

      # Etc
      LESSHISTFILE = "${config.xdg.cacheHome}/lesshst";
      MYSQL_HISTFILE = "${config.xdg.cacheHome}/mysql_history";
    };

    shellAliases = {
      l = "lsd -l";
      ls = "lsd -al";
      mubectl = "minikube kubectl --";
    };

    initExtraFirst = ''
      # Powerlevel10k instant prompt
      if [[ -r "$HOME/.cache/p10k-instant-prompt-''${(%):-%n}.zsh" ]]; then
        source "$HOME/.cache/p10k-instant-prompt-''${(%):-%n}.zsh"
      fi
    '';

    initExtraBeforeCompInit = ''
      # Use word jump for zsh, tmux
      bindkey "^[[1;5C" forward-word
      bindkey "^[[1;5D" backward-word
      bindkey "^[[1;3C" forward-word
      bindkey "^[[1;3D" backward-word

      # Powerlevel10k theme
      source "${config.xdg.configHome}/zsh/.p10k.zsh"
    '';

    initExtra = ''
      setopt globdots

      # Add awscli2 completion
      source ${pkgs.awscli2}/share/zsh/site-functions/aws_zsh_completer.sh
    '';

    profileExtra = "
      # do nothing
    ";
  };
}
