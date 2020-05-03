#!/bin/bash

# easy add ppa
add_ppa() {
  wget -qO - "$2" | mute sudo apt-key add -
  echo "$3" | silent sudo tee "/etc/apt/sources.list.d/$1.list"
}
