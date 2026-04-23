{ ... }:

let
  colors = import ../../colors.nix;

in
{
  programs.tmux = {
    enable = true;
    keyMode = "vi";
    terminal = "tmux-256color";
    extraConfig = ''
      # terminal features
      set -as terminal-features ',xterm-256color:RGB:extkeys'
      set -as terminal-features ',wezterm:RGB:extkeys'
      set -as terminal-features ',tmux-256color:RGB:extkeys'

      # term
      set -g allow-passthrough on
      set -g extended-keys on
      set -g history-limit 100000

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
      set -g status-bg "${colors.brights.green}"
      set -g status-fg "${colors.ansi.black}"
    '';
  };
}
