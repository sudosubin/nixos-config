#!/bin/bash

set_wallpaper() {
  # Directory
  local current_dir
  local script_dir
  local app_dir

  current_dir="$(dirname "${BASH_SOURCE[0]}")"
  script_dir="$(dirname "$current_dir")"
  app_dir="$(dirname "$(dirname "$(dirname "$script_dir")")")"

  # shellcheck source=../../../../src/utils/msg.sh
  source "$app_dir/src/utils/msg.sh"
  # shellcheck source=../../../../src/utils/stdout.sh
  source "$app_dir/src/utils/stdout.sh"

  # Set wallpaper
  msg_step "Set wallpaper to all desktops"

  mkdir -p ~/.local/share/wallpapers
  cp -r "$script_dir/wallpapers/background.jpg" \
    ~/.local/share/wallpapers/background.jpg

  echo \
    "qdbus org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.evaluateScript '
      var allDesktops = desktops();
      for (i = 0; i < allDesktops.length; i++) {
        d = allDesktops[i];
        d.wallpaperPlugin = \"org.kde.image\";
        d.currentConfigGroup = Array(
          \"Wallpaper\", \"org.kde.image\", \"General\"
        );
        d.writeConfig(
          \"Image\", \"file://$HOME/.local/share/wallpapers/background.jpg\"
        );
      }
    '" | bash

  # Set lock screen wallpaper
  kwriteconfig5 --file kscreenlockerrc \
    --group Greeter --group Wallpaper --group org.kde.image --group General \
    --key Image "file://$HOME/.local/share/wallpapers/background.jpg"
}
