# Set up the prompt

autoload -Uz promptinit
promptinit

setopt autocd histignorealldups sharehistory

# Use word jump for zsh, tmux
bindkey "5C" forward-word
bindkey ";5C" forward-word
bindkey "5D" backward-word
bindkey ";5D" backward-word

# Keep 1000 lines of history within the shell and save it to ~/.zsh_history:
HISTSIZE=1000
SAVEHIST=1000
HISTFILE=~/.zsh_history

# Use modern completion system
zstyle ':completion:*' auto-description 'specify: %d'
zstyle ':completion:*' completer _expand _complete _correct _approximate
zstyle ':completion:*' format 'Completing %d'
zstyle ':completion:*' group-name ''
zstyle ':completion:*' menu select=2
eval "$(dircolors -b)"
zstyle ':completion:*:default' list-colors ${(s.:.)LS_COLORS}
zstyle ':completion:*' list-colors ''
zstyle ':completion:*' list-prompt %SAt %p: Hit TAB for more, or the character to insert%s
zstyle ':completion:*' matcher-list '' 'm:{a-z}={A-Z}' 'm:{a-zA-Z}={A-Za-z}' 'r:|[._-]=* r:|=* l:|=*'
zstyle ':completion:*' menu select=long
zstyle ':completion:*' select-prompt %SScrolling active: current selection at %p%s
zstyle ':completion:*' use-compctl false
zstyle ':completion:*' verbose true

zstyle ':completion:*:*:kill:*:processes' list-colors '=(#b) #([0-9]#)*=0=01;31'
zstyle ':completion:*:kill:*' command 'ps -u $USER -o pid,%cpu,tty,cputime,cmd'


### Added by Zinit's installer
source "$HOME/.zinit/bin/zinit.zsh"
autoload -Uz _zinit
(( ${+_comps} )) && _comps[zinit]=_zinit

# Load a few important annexes, without Turbo
# (this is currently required for annexes)
zinit light-mode for \
    zinit-zsh/z-a-patch-dl \
    zinit-zsh/z-a-as-monitor \
    zinit-zsh/z-a-bin-gem-node

### End of Zinit's installer chunk

# Async
zinit ice pick'async.zsh'
zinit light mafredri/zsh-async

# Theme
SPACESHIP_CHAR_SYMBOL=' '
zinit light denysdovhan/spaceship-prompt

# Plugins > Core
ZSH_AUTOSUGGEST_HIGHLIGHT_STYLE='fg=#808080'

zinit light-mode wait lucid for \
    atinit'ZINIT[COMPINIT_OPTS]=-C; zicompinit; zicdreplay' \
        zdharma/fast-syntax-highlighting \
    blockf \
        zsh-users/zsh-completions \
    atload'!_zsh_autosuggest_start' \
        zsh-users/zsh-autosuggestions

# Plugins > asdf
zinit ice pick'asdf.plugin.zsh' atinit'autoload bashcompinit; bashcompinit' blockf
zinit light kiurchv/asdf.plugin.zsh

# Plugins > auto-update
zinit ice wait lucid pick'update.sh'
zinit light sudosubin/auto-update

# Plugins > fzf
zplugin ice wait lucid pick'shell/key-bindings.zsh' src'shell/completion.zsh'
zplugin light junegunn/fzf

# Plugins > k
alias l=k
alias ls='k -a'
zinit ice wait lucid pick'k.sh'
zinit light supercrabtree/k

# Softwares > vscodium
alias code=codium
