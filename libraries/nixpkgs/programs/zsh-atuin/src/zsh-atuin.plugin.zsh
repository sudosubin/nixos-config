export ATUIN_NOBIND=1
source <(atuin init zsh)
unset ATUIN_NOBIND

ZSH_AUTOSUGGEST_STRATEGY=('atuin')  # _zsh_autosuggest_strategy_atuin
ZSH_AUTOSUGGEST_CLEAR_WIDGETS+=('atuin-up-line-or-history')
ZSH_AUTOSUGGEST_CLEAR_WIDGETS+=('atuin-down-line-or-history')

_atuin-history() {
  local SCRIPT_DIR=${${(%):-%x}:A:h}
  $SCRIPT_DIR/bin/zsh-atuin "$@"
}

atuin-history-widget() {
  local AUTIN_FZF_DEFAULT_OPTS="--height ${FZF_TMUX_HEIGHT:-40%} $FZF_DEFAULT_OPTS --ansi --tiebreak=index --bind=ctrl-r:toggle-sort,ctrl-z:ignore $FZF_CTRL_R_OPTS --query=${(qqq)LBUFFER} +m"

  output=$(_atuin-history | FZF_DEFAULT_OPTS="$AUTIN_FZF_DEFAULT_OPTS" fzf)

	if [[ -n $output ]] ; then
    command=$(/usr/bin/env python3 -c "import sys; print(sys.argv[1].strip().split(maxsplit=3)[-1])" "$output")
		LBUFFER=$(echo $command)
	fi

  zle reset-prompt
}

_zsh_autosuggest_strategy_atuin() {
  # Reset options to defaults and enable LOCAL_OPTIONS
  emulate -L zsh

  # Enable globbing flags
	setopt EXTENDED_GLOB

  # Escape backslashes and all of the glob operators
  local prefix="${1//(#m)[\\*?[\]<>()|^~#]/\\$MATCH}"

  # Get the history items that match the prefix, excluding those that match
	# the ignore pattern
	local pattern="$prefix*"
	if [[ -n $ZSH_AUTOSUGGEST_HISTORY_IGNORE ]]; then
		pattern="($pattern)~($ZSH_AUTOSUGGEST_HISTORY_IGNORE)"
	fi

  # Give the first history item matching the pattern as the suggestion
  atuin_history=("${(@f)$(_atuin-history --columns=command)}")
	typeset -g suggestion="${atuin_history[(r)$pattern]}"
}

_atuin-line-or-history() {
  local operator="$1"
  typeset -g suggestion=""
}

atuin-up-line-or-history() {
  _atuin-line-or-history "+"
}

atuin-down-line-or-history() {
  _atuin-line-or-history "-"
}

zle -N atuin-history-widget
bindkey -M emacs '^R' atuin-history-widget
bindkey -M vicmd '^R' atuin-history-widget
bindkey -M viins '^R' atuin-history-widget

zle -N atuin-up-line-or-history
zle -N atuin-down-line-or-history
bindkey '^[[A' atuin-up-line-or-history
bindkey '^[[B' atuin-down-line-or-history
