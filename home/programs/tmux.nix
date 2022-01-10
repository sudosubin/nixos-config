{ config, pkgs, ... }:

{
  home.packages = with pkgs; [
    tmux
  ];

  programs.tmux = {
    enable = true;
    terminal = "screen-256color";
    extraConfig = ''
      set -ga terminal-overrides ',*-256color*:Tc'

      # ctrl+b highlight
      set -g status-right '#{?client_prefix,#[reverse] ^B #[noreverse],} | %a %Y-%m-%d %H:%M'

      # open new window/pane from current path
      bind '"' split-window -c "#{pane_current_path}"
      bind % split-window -h -c "#{pane_current_path}"
      bind c new-window -c "#{pane_current_path}"

      # bottom status bar color
      set -g status-bg green
      set -g status-fg '#1e2127'
    '';
  };
}
