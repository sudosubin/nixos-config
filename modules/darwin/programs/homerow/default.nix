{ ... }:

{
  services.homerow = {
    enable = true;

    config = {
      check-for-updates-automatically = false;
      dash-speed-multiplier = 2;
      label-font-size = 10;
      non-search-shortcut = "⌥⌘Space"; # ⌥⌘Space
      scroll-px-per-ms = 1.5;
      search-shortcut = "⌥⌘↩"; # ⌥⌘↩
    };
  };
}
