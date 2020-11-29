#!/bin/bash

# Directory
current_dir="$(dirname "${BASH_SOURCE[0]}")"
script_dir="$(dirname "$current_dir")"
app_dir="$(dirname "$(dirname "$(dirname "$script_dir")")")"

# shellcheck source=requirements.sh
source "$script_dir/libs/requirements.sh"

# shellcheck source=applet-window-appmenu.sh
source "$script_dir/libs/applet-window-appmenu.sh"

# shellcheck source=applet-window-buttons.sh
source "$script_dir/libs/applet-window-buttons.sh"

# shellcheck source=asdf.sh
source "$script_dir/libs/asdf.sh"

# shellcheck source=bat.sh
source "$script_dir/libs/bat.sh"

# shellcheck source=capitaine-cursors.sh
source "$script_dir/libs/capitaine-cursors.sh"

# shellcheck source=delta.sh
source "$script_dir/libs/delta.sh"

# shellcheck source=hello.sh
source "$script_dir/libs/hello.sh"

# shellcheck source=la-capitaine-icon-theme.sh
source "$script_dir/libs/la-capitaine-icon-theme.sh"

# shellcheck source=latte.sh
source "$script_dir/libs/latte.sh"

# shellcheck source=tian.sh
source "$script_dir/libs/tian.sh"

# shellcheck source=plank.sh
source "$script_dir/libs/plank.sh"

# shellcheck source=spotify.sh
source "$script_dir/libs/spotify.sh"

# shellcheck source=st.sh
source "$script_dir/libs/st.sh"

# shellcheck source=tmux.sh
source "$script_dir/libs/tmux.sh"

# shellcheck source=ulauncher.sh
source "$script_dir/libs/ulauncher.sh"

# shellcheck source=zsh.sh
source "$script_dir/libs/zsh.sh"
