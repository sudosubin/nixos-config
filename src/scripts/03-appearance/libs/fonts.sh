#!/bin/bash

set_fonts() {
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

  # Set fonts: SF Pro Text
  msg_step "Set fonts: SF Pro Text"

  local fonts_dir="$HOME/.local/share/fonts"
  local sf_pro_text_dir="$HOME/.local/share/fonts/SF Pro Text"

  # copy to local fonts directory
  msg_normal "copy to local fonts directory"
  mkdir -p "$fonts_dir"
  cp -r "$script_dir/fonts/SF Pro Text" "$sf_pro_text_dir"

  # set global fonts (gsettings)
  gsettings set org.gnome.desktop.interface \
    font-name 'SF Pro Text 10'
  gsettings set org.gnome.desktop.interface \
    document-font-name 'SF Pro Text 10'
  gsettings set org.gnome.desktop.wm.preferences \
    titlebar-font 'SF Pro Text Semibold 10'

  # set global fonts (plasma)
  kwriteconfig5 --file kdeglobals --group General \
    --key font "SF Pro Text,10,-1,5,50,0,0,0,0,0"
  kwriteconfig5 --file kdeglobals --group General \
    --key menuFont "SF Pro Text,10,-1,5,50,0,0,0,0,0"
  kwriteconfig5 --file kdeglobals --group General \
    --key smallestReadableFont "SF Pro Text,8,-1,5,50,0,0,0,0,0"
  kwriteconfig5 --file kdeglobals --group General \
    --key toolBarFont "SF Pro Text,10,-1,5,50,0,0,0,0,0"
  kwriteconfig5 --file kdeglobals --group WM \
    --key activeFont "SF Pro Text,10,-1,5,63,0,0,0,0,0,Semibold"
  kwriteconfig5 --file ~/.kde/share/config/kdeglobals --group General \
    --key font "SF Pro Text,10,-1,5,50,0,0,0,0,0"
  kwriteconfig5 --file ~/.kde/share/config/kdeglobals --group General \
    --key menuFont "SF Pro Text,10,-1,5,50,0,0,0,0,0"
  kwriteconfig5 --file ~/.kde/share/config/kdeglobals --group General \
    --key smallestReadableFont "SF Pro Text,8,-1,5,50,0,0,0,0,0"
  kwriteconfig5 --file ~/.kde/share/config/kdeglobals --group General \
    --key toolBarFont "SF Pro Text,10,-1,5,50,0,0,0,0,0"

  # set global fonts (etc)
  kwriteconfig5 --file ~/.config/gtk-3.0/settings.ini --group Settings \
    --key gtk-font-name "SF Pro Text,  10"

  sed -i -E "s|^Gtk\/FontName.*|Gtk/FontName \"SF Pro Text,  10\"|g" \
    ~/.config/xsettingsd/xsettingsd.conf

  # Set fonts: FiraMono Nerd Font Mono
  msg_step "Set fonts: FiraMono Nerd Font Mono (from online)"

  local firamono_dir="$HOME/.local/share/fonts/FiraMono"

  # download from github repository
  msg_normal "download fonts from github repository"
  # TODO (sudosubin): remove after test complete
  rm -rf "$firamono_dir"
  mkdir -p "$firamono_dir"

  # shellcheck disable=SC2190
  declare -a weights=("Bold" "Medium" "Regular")

  for weight in "${weights[@]}"; do
    msg_normal "download FiraMono $weight"
    curl -sL "https://github.com/ryanoasis/nerd-fonts/raw/\
master/patched-fonts/FiraMono/$weight/complete/\
Fira%20Mono%20$weight%20Nerd%20Font%20Complete%20Mono.otf" \
      -o "$firamono_dir/FiraMono $weight.otf"
  done

  # set plasma, gsettings
  kwriteconfig5 --file kdeglobals --group General \
    --key fixed "FiraMono Nerd Font Mono,10,-1,5,50,0,0,0,0,0"
  gsettings set org.gnome.desktop.interface \
    monospace-font-name "FiraMono Nerd Font Mono 10"

  # set custom fontconfig
  msg_normal "set custom fontconfig"
  mkdir -p ~/.config/fontconfig
  cp "$script_dir/fonts/fonts.conf" \
    "$HOME/.config/fontconfig/fonts.conf"

}
