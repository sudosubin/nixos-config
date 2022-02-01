{ config, pkgs, ... }:

{
  home.packages = with pkgs; [
    zsh
  ];

  xdg.configFile = {
    "zsh/.p10k.zsh".source = ./files/.p10k.zsh;
  };

  programs.zsh = {
    enable = true;
    enableCompletion = true;
    dotDir = ".config/zsh";

    autocd = true;
    history.ignoreDups = true;
    history.ignoreSpace = true;

    plugins = [
      {
        name = "zsh-powerlevel10k";
        src = pkgs.zsh-powerlevel10k;
        file = "share/zsh-powerlevel10k/powerlevel10k.zsh-theme";
      }
      {
        name = "zsh-autopair";
        src = pkgs.zsh-autopair;
        file = "share/zsh/zsh-autopair/autopair.zsh";
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
    ];

    sessionVariables = {
      # Node.js
      NEXT_TELEMETRY_DISABLED = "1";
      NPM_CONFIG_DEVDIR = "/tmp/.gyp";
      NODE_REPL_HISTORY = "${config.xdg.cacheHome}/node_repl_history";

      # Jetbrains
      _JAVA_AWT_WM_NONREPARENTING = "1";
    };

    shellAliases = {
      l = "ll";
      ls = "ll -a";
      code = "codium";
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

      # Powerlevel10k theme
      source "$HOME/.config/zsh/.p10k.zsh"
    '';

    initExtra = ''
      setopt globdots

      # Add awscli2 completion
      source ${pkgs.awscli2}/share/zsh/site-functions/aws_zsh_completer.sh
    '';
  };
}
