#!/bin/sh

set -e

# root="$(dirname "$(dirname "$(readlink -f "$0")")")"

message() {
    echo "$(tput setaf 2)$*$(tput sgr 0)"
}

# Install ansible
if ! which ansible >/dev/null; then
    message "Install ansible"
    echo "deb http://ppa.launchpad.net/ansible/ansible/ubuntu focal main" \
        | sudo tee /etc/apt/sources.list.d/ansible.list >/dev/null

    sudo apt-key adv \
        --keyserver keyserver.ubuntu.com \
        --recv-keys 93C4A3FD7BB9C367 >/dev/null 2>&1

    sudo apt update

    sudo apt install --yes --no-install-recommends ansible
fi
