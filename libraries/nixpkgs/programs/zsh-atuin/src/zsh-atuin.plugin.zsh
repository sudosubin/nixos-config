export ATUIN_NOBIND=1
source <(atuin init zsh)
unset ATUIN_NOBIND

_atuin_history() {
  local SCRIPT_DIR=${${(%):-%x}:A:h}
  $SCRIPT_DIR/bin/zsh-atuin "$@"
}

_atuin_history_widget() {
  local SCRIPT_DIR=${${(%):-%x}:A:h}
  local AUTIN_FZF_DEFAULT_OPTS="--height ${FZF_TMUX_HEIGHT:-40%} $FZF_DEFAULT_OPTS --ansi --tiebreak=index --bind=ctrl-r:toggle-sort,ctrl-z:ignore $FZF_CTRL_R_OPTS --query=${(qqq)LBUFFER} +m"

  output=$(_atuin_history | FZF_DEFAULT_OPTS="$AUTIN_FZF_DEFAULT_OPTS" fzf)

	if [[ -n $output ]] ; then
    command=$(/usr/bin/env python3 -c "import sys; print(sys.argv[1].strip().split(maxsplit=3)[-1])" "$output")
		LBUFFER=$(echo $command)
	fi

  zle reset-prompt
}

zle -N _atuin_history_widget
bindkey '^R' _atuin_history_widget
