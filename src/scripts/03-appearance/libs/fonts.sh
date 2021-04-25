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

  # Set fonts: FiraMono Nerd Font Mono
  msg_step "Set fonts: FiraMono Nerd Font Mono (from online)"

  local firamono_dir="$HOME/.local/share/fonts/FiraMono"

  # download from github repository
  msg_normal "download fonts from github repository"
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

  gsettings set org.gnome.desktop.interface \
    monospace-font-name "FiraMono Nerd Font Mono 10"
}
