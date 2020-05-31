#!/bin/bash

install_st() {
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
  # shellcheck disable=SC1090
  source "$HOME/.asdf/asdf.sh"

  # Configure st
  msg_step "Install st"

  msg_normal "clone from git"
  mute git clone https://github.com/LukeSmithxyz/st.git ./temp-git

  msg_normal "build and install"
  cd temp-git || exit
  silent sudo make install
  cd ..
  rm -rf temp-git

  msg_normal "copy settings to local"
  cp "$script_dir/settings/.Xresources" ~/.Xresources

  msg_normal "copy application desktop"
  sudo cp "$script_dir/settings/st.desktop" \
    "/usr/share/applications/st.desktop"

  msg_normal "make st-term as a default shell"
  kwriteconfig5 --file kdeglobals --group General \
    --key TerminalApplication "st"

  msg_normal "change global shortcuts"

  sudo ln -s /usr/share/applications/st.desktop \
    /usr/share/kglobalaccel/st.desktop

  kwriteconfig5 --file kglobalshortcutsrc \
    --group st.desktop \
    --key New "none,none,New Terminal"
  kwriteconfig5 --file kglobalshortcutsrc \
    --group st.desktop \
    --key _k_friendly_name "Launch Terminal"
  kwriteconfig5 --file kglobalshortcutsrc \
    --group st.desktop \
    --key _launch "Ctrl+Alt+T,none,Launch Terminal"
}
