#!/bin/bash

# Colors
## Colors > Common
prefix="\033["
suffix="\033[0m"

## Colors > Weights
declare -A weights=(
  ["normal"]="0;"
  ["bold"]="1;"
)

## Colors > Colors
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

## Colors > Pprint (pretty print)
function pprint {
  weight="${weights[$1]}"
  color="${colors[$2]}"
  message="${@:3}"

  echo -e "${prefix}${weight}${color}${message}${suffix}"
}
