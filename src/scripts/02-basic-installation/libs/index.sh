#!/bin/bash

# Directory
current_dir="$(dirname "${BASH_SOURCE[0]}")"
script_dir="$(dirname "$current_dir")"
app_dir="$(dirname "$(dirname "$(dirname "$script_dir")")")"

# shellcheck source=requirements.sh
source "$script_dir/libs/requirements.sh"

# shellcheck source=alacritty.sh
source "$script_dir/libs/alacritty.sh"

# shellcheck source=applet-window-appmenu.sh
source "$script_dir/libs/applet-window-appmenu.sh"

# shellcheck source=applet-window-buttons.sh
source "$script_dir/libs/applet-window-buttons.sh"

# shellcheck source=hello.sh
source "$script_dir/libs/hello.sh"

# shellcheck source=kime.sh
source "$script_dir/libs/kime.sh"

# shellcheck source=la-capitaine-icon-theme.sh
source "$script_dir/libs/la-capitaine-icon-theme.sh"

# shellcheck source=latte.sh
source "$script_dir/libs/latte.sh"

# shellcheck source=plank.sh
source "$script_dir/libs/plank.sh"

# shellcheck source=ulauncher.sh
source "$script_dir/libs/ulauncher.sh"

# shellcheck source=vscodium.sh
source "$script_dir/libs/vscodium.sh"

# shellcheck source=zpl.sh
source "$script_dir/libs/zpl.sh"

# shellcheck source=zsh.sh
source "$script_dir/libs/zsh.sh"
