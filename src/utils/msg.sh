#!/bin/bash

# pretty print
msg() {
  declare -A weights=(
    ["normal"]="0;"
    ["bold"]="1;"
  )

  declare -A colors=(
    ["black"]="30m"
    ["red"]="31m"
    ["green"]="32m"
    ["yellow"]="33m"
    ["blue"]="34m"
    ["purple"]="35m"
    ["cyan"]="36m"
    ["white"]="37m"
  )

  local weight="${weights[$1]}"
  local color="${colors[$2]}"
  local message="${*:3}"

  echo -e "\033[${weight}${color}${message}\033[0m"
}

# pretty print title
msg_title() {
  msg bold blue "$*"
}

# pretty print subtitle
msg_subtitle() {
  msg bold green "> $*"
}

# pretty print step
msg_step() {
  msg normal yellow "  - $*"
}

# print line without style
msg_line() {
  echo "    • $*"
}

# new empty line
new_line() {
  echo ""
}
