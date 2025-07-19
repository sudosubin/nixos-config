{ config, pkgs, ... }:

{
  programs.tmux = {
    enable = true;
    keyMode = "vi";
    terminal = "screen-256color";
    extraConfig = ''
      set -ga terminal-overrides ',*-256color*:Tc'

      # ctrl+b highlight
      set -g status-right '#{?client_prefix,#[reverse] ^B #[noreverse],} | %a %Y-%m-%d %H:%M'

      # vim binding
      bind h select-pane -L
      bind j select-pane -D
      bind k select-pane -U
      bind l select-pane -R

      # pane resize binding
      bind -r H resize-pane -L 5
      bind -r J resize-pane -D 5
      bind -r K resize-pane -U 5
      bind -r L resize-pane -R 5

      # open new window/pane from current path
      bind '"' split-window -c "#{pane_current_path}"
      bind % split-window -h -c "#{pane_current_path}"
      bind c new-window -c "#{pane_current_path}"

      # bottom status bar color
      set -g status-bg green
      set -g status-fg black
    '';
  };
}
