#!/bin/bash


# Directory
CURRENT_DIR="$(dirname "${BASH_SOURCE[0]}")"
APP_DIR="$(dirname "$(dirname "$(dirname "$CURRENT_DIR")")")"


# Function
# shellcheck source=../../../src/utils/msg.sh
source "$APP_DIR/src/utils/msg.sh" ":"
# shellcheck source=../../../src/utils/stdout.sh
source "$APP_DIR/src/utils/stdout.sh" ":"


# Title
msg_title "02. Basic Installation"


# Install softwares
msg_subtitle "Install softwares"

## Install softwares: via apt-get
## - git curl: Basic for script installation
## - nimf nimf-libhangul: Basic for Korean input
## - latte-dock applet-window-buttons: For better appearance
## - chromium-browser codium net-tools fzf yarn zsh: My personal preference
## - cmake g++ extra-cmake-modules libkdecorations2-dev
##   libkf5guiaddons-dev libkf5configwidgets-dev
##   libkf5windowsystem-dev libkf5package-dev libqt5x11extras5-dev
##   gettext pkg-config: Build-deps for kde-hello window decoration
## - qttools5-dev libkf5crash-dev libkf5globalaccel-dev
##   libkf5kio-dev libkf5notifications-dev
##   kinit-dev kwin-dev: Build-deps for kde-hello kwin effects
## - inkscape x11-apps: Build-deps for capitaine-cursors
msg_step "Install packages via apt-get"
hr
sudo apt-get -y --no-install-recommends install \
  git curl \
  nimf nimf-libhangul \
  latte-dock applet-window-buttons \
  chromium-browser codium net-tools fzf yarn zsh \
  cmake g++ extra-cmake-modules libkdecorations2-dev \
  libkf5guiaddons-dev libkf5configwidgets-dev \
  libkf5windowsystem-dev libkf5package-dev libqt5x11extras5-dev \
  gettext pkg-config \
  qttools5-dev libkf5crash-dev libkf5globalaccel-dev \
  libkf5kio-dev libkf5notifications-dev \
  kinit-dev kwin-dev \
  inkscape x11-apps
hr
new_line

## Install softwares: asdf-vm
msg_step "Install asdf-vm"

### Install softwares: asdf-vm via git
msg_line "asdf-vm clone from git"
mute git clone https://github.com/asdf-vm/asdf.git ~/.asdf

### Install softwares: asdf-vm latest
msg_line "asdf-vm set to use latest from git"
mute git -C ~/.asdf checkout "$(git -C ~/.asdf describe --abbrev=0 --tags)"

## Install softwares: zsh
msg_step "Configure zsh & zinit"

### Install softwares: zsh make default shell
msg_line "make zsh default shell"
pam_required="required   pam_shells.so"
pam_sufficient="sufficient   pam_shells.so"
sudo sed -iE "s/$pam_required/$pam_sufficient/g" /etc/pam.d/chsh
chsh -s "$(command -v zsh)"
sudo sed -iE "s/$pam_sufficient/$pam_required/g" /etc/pam.d/chsh

### Install softwares: zsh zinit
msg_line "install zinit from git"
mute git clone https://github.com/zdharma/zinit.git ~/.zinit/bin

### Install softwares: settigns
msg_line "copy .zshrc, .zshenv"
cp "$CURRENT_DIR/settings/.zshrc" ~/.zshrc
cp "$CURRENT_DIR/settings/.zshenv" ~/.zshenv


# Configure softwares
msg_subtitle "Configure softwares"

## Configure softwares: nimf
msg_step "Configure nimf"

### Configure softwares: nimf default input
msg_line "make nimf default im"
im-config -n nimf

### Configure softwares: nimf keys
msg_line "configure nimf keys"
hangul_keys="['Hangul', 'Alt_R']"
hanja_keys="['Hangul_Hanja', 'Control_R']"
xkb_option_ctrl="'ctrl:menu_rctrl', 'ctrl:swapcaps'"
xkb_option_korean="'korean:ralt_hangul', 'korean:rctrl_hanja'"
xkb_options="[$xkb_option_ctrl, $xkb_option_korean]"
gsettings set org.nimf setup-environment-variables true
gsettings set org.nimf hotkeys "$hangul_keys"
gsettings set org.nimf.clients.gtk hook-gdk-event-key true
gsettings set org.nimf.clients.gtk reset-on-gdk-button-press-event false
gsettings set org.nimf.settings xkb-options "$xkb_options"
gsettings set org.nimf.engines.nimf-libhangul shortcuts-to-sys "$hangul_keys"
gsettings set org.nimf.engines.nimf-libhangul shortcuts-to-lang "$hangul_keys"
gsettings set org.nimf.engines.nimf-libhangul hanja-keys "$hanja_keys"

## Configure softwares: vscodium
msg_step "Configure vscodium"

### Configure softwares: vscodium extensions
### - zhuangtongfa.Material-theme: One Dark Pro Theme
### - PKief.material-icon-theme: Material Icon Theme
### - ms-python.python: Python Language support
### - timonwong.shellcheck: Bash style checker
### - mrorz.language-gettext: gettext(.po) Syntax support
### - GitHub.vscode-pull-request-github: GitHub PR from codium
### - eamodio.gitlens: Git blame in codium
msg_line "install vscodium extensions"
silent codium --install-extension zhuangtongfa.Material-theme
silent codium --install-extension PKief.material-icon-theme
silent codium --install-extension ms-python.python
silent codium --install-extension timonwong.shellcheck
silent codium --install-extension mrorz.language-gettext
silent codium --install-extension GitHub.vscode-pull-request-github
silent codium --install-extension eamodio.gitlens

### Configure softwares: vscodium settings
msg_line "configure vscodium settings"
cp "$CURRENT_DIR/settings/vscodium.json" ~/.config/VSCodium/User/settings.json


# Build softwares
msg_subtitle "Build softwares"

## Build softwares: capitaine-cursors
# TODO (sudosubin): install actually to system
msg_step "Build capitaine-cursors"

## Build softwares: capitaine-cursors via git
msg_line "clone from git"
mute git clone https://github.com/keeferrourke/capitaine-cursors.git \
  ./temp-git

### Build softwares: capitaine-cursors build
msg_line "build capitaine-cursors"
cd temp-git || exit
mute ./build.sh -t dark
cd ..

### Build softwares: capitaine-cursors copy
msg_line "copy to cursors path"
cp -r temp-git/dist/dark ~/.icons/capitaine-cursors

### Build softwares: capitaine-cursors clean
msg_line "clean up"
rm -rf temp-git

## Build softwares: la-capitaine-icon-theme
# TODO (sudosubin): install actually to system
msg_step "Build la-capitaine-icon-theme"

## Build softwares: la-capitaine-icon-theme via git
msg_line "clone from git"
mute git clone https://github.com/keeferrourke/la-capitaine-icon-theme.git \
  ./temp-git

### Build softwares: la-capitaine-icon-theme build
msg_line "build la-capitaine-icon-theme"
cd temp-git || exit
echo y | mute ./configure
cd ..

### Build softwares: la-capitaine-icon-theme copy
msg_line "copy to icon path"
cp -r temp-git ~/.local/share/icons/la-capitaine-icon-theme

### Build softwares: la-capitaine-icon-theme clean
msg_line "clean up"
rm -rf temp-git

## Build softwares: kde-hello
msg_step "Build kde-hello"

### Build softwares: kde-hello via git
msg_line "clone from git"
mute git clone https://github.com/n4n0GH/hello.git ./temp-git

### Build softwares: kde-hello checkout
msg_line "checkout to older version (transparency shades fix)"
mute git -C temp-git checkout 3a4d3e2530109280b4bc8bd472e6c2037176839b

### Build softwares: kde-hello window-decoration
msg_line "build window-decoration"
mkdir -p temp-git/window-decoration/build
cd temp-git/window-decoration/build || exit
hr
cmake -DCMAKE_INSTALL_PREFIX=/usr ..
make
sudo make install
hr
new_line
cd ../../..

### Build softwares: kde-hello kwin-effects
msg_line "build kwin-effects"
mkdir -p temp-git/kwin-effects/qt5build
cd temp-git/kwin-effects/qt5build || exit
hr
cmake -DCMAKE_INSTALL_PREFIX=/usr -DQT5BUILD=ON ..
make
sudo make install
hr
new_line
cd ../../..

### Build softwares: kde-hello clean
msg_line "clean up"
rm -rf temp-git
