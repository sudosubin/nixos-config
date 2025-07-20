local wezterm = require 'wezterm'

return {
  automatically_reload_config = true,
  color_scheme = "default",
  font = wezterm.font_with_fallback {
    { family = "PragmataProMono Nerd Font Mono" },
    { family = "Apple Color Emoji", assume_emoji_presentation = true },
  },
  font_size = 13,
  front_end = "WebGpu",
  hide_tab_bar_if_only_one_tab = true,
  keys = {
    { mods = "SHIFT", key = "Enter", action = wezterm.action.SendString '\n' },
    { mods = "LEADER|CTRL", key = "b", action = wezterm.action.SendKey { mods = 'CTRL', key = 'b' } },
    { mods = "LEADER", key = '"', action = wezterm.action.SplitVertical { domain = 'CurrentPaneDomain' } },
    { mods = "LEADER", key = '%', action = wezterm.action.SplitHorizontal { domain = 'CurrentPaneDomain' } },
    { mods = "LEADER", key = "z", action = wezterm.action.TogglePaneZoomState },
    { mods = "LEADER", key = "p", action = wezterm.action.PaneSelect { alphabet = '0123456789' } },
    { mods = "LEADER", key = "x", action = wezterm.action.CloseCurrentPane { confirm = true } },
    { mods = "LEADER", key = "h", action = wezterm.action.ActivatePaneDirection 'Left' },
    { mods = "LEADER", key = "l", action = wezterm.action.ActivatePaneDirection 'Right' },
    { mods = "LEADER", key = "j", action = wezterm.action.ActivatePaneDirection 'Down' },
    { mods = "LEADER", key = "k", action = wezterm.action.ActivatePaneDirection 'Up' },
    { mods = "LEADER", key = "r", action = wezterm.action.ActivateKeyTable { name = 'resize-pane', one_shot = false } },
    { mods = "LEADER", key = "c", action = wezterm.action.ActivateKeyTable { name = 'rotate-pane', one_shot = false } },
  },
  key_tables = {
    ["resize-pane"] = {
      { key = "h", action = wezterm.action.AdjustPaneSize { 'Left', 1 } },
      { key = "l", action = wezterm.action.AdjustPaneSize { 'Right', 1 } },
      { key = "j", action = wezterm.action.AdjustPaneSize { 'Down', 1 } },
      { key = "k", action = wezterm.action.AdjustPaneSize { 'Up', 1 } },
      { key = "Escape", action = wezterm.action.PopKeyTable }
    },
    ["rotate-pane"] = {
      { key = "h", action = wezterm.action.RotatePanes 'Clockwise' },
      { key = "l", action = wezterm.action.RotatePanes 'CounterClockwise' },
      { key = "j", action = wezterm.action.RotatePanes 'Clockwise' },
      { key = "k", action = wezterm.action.RotatePanes 'CounterClockwise' },
      { key = "Escape", action = wezterm.action.PopKeyTable }
    }
  },
  leader = { key = 'b', mods = 'CTRL', timeout_milliseconds = 1000 },
  window_decorations = "RESIZE"
};
