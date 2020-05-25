# Personal KDE setup script

This is a personal KDE setup script. I made this script to set up my laptop and computer easily, keep in sync.

## Requires

- First boot, with Kubuntu 20.04 LTS

## Sources

- Wallpaper: Never Settle Wallpapers

## Installation

```sh
# install git
sudo apt update
sudo apt -y upgrade
sudo apt install git

# git clone
git clone https://github.com/sudosubin/setup-script.git
sh setup-script/install.sh
```

### for Surface device

Do below together.

```sh
sudo apt -y install linux-headers-surface linux-image-surface linux-libc-dev-surface surface-ipts-firmware libwacom-surface linux-surface-secureboot-mok
```

### Secure notes

- `rclone conf`
- `keepassxc db`
- `pip.conf`
- `ufw rules`


## Contribute

It is a personal script, so some requests might not be admitted. (eg. Changing shortcuts, themes, etc.)

But better syntax, comments, or enhancement of performance are all welcomed. Feel free to make a pull request, or fork
this project.
