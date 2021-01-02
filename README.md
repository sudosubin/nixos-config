# Personal KDE setup script

This is a personal KDE setup script. I made this script to set up my laptop and computer easily, keep in sync.

## Requires

- First boot, with Kubuntu 20.04.1 LTS

## Installation

```sh
# install git
sudo apt update
sudo apt -y upgrade
sudo apt install git curl wget --no-install-recommends

# git clone
git clone https://github.com/sudosubin/setup-script.git
sh setup-script/install.sh
```

### for Surface device

Do below together.

```sh
# Add package repository
wget -qO - https://raw.githubusercontent.com/linux-surface/linux-surface/master/pkg/keys/surface.asc \
    | sudo apt-key add -

echo "deb [arch=amd64] https://pkg.surfacelinux.com/debian release main" \
    | sudo tee /etc/apt/sources.list.d/linux-surface.list

# Install
sudo apt -y install linux-headers-surface linux-image-surface surface-ipts-firmware libwacom-surface iptsd linux-surface-secureboot-mok
```

## Sources

- Wallpaper: Never Settle Wallpapers

## Contribute

It is a personal script, so some requests might not be admitted. (eg. Changing shortcuts, themes, etc.)

But better syntax, comments, or enhancement of performance are all welcomed. Feel free to make a pull request, or fork
this project.

## License

Setup Script is [MIT Licensed](./LICENSE).
