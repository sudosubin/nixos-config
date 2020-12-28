# Powerlevel10k instant prompt.
if [[ -r "$HOME/.cache/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
    source "$HOME/.cache/p10k-instant-prompt-${(%):-%n}.zsh"
fi

# Set up the prompt
autoload -Uz promptinit
promptinit

setopt autocd histignorealldups sharehistory

# Use word jump for zsh, tmux
bindkey "^[[1;5C" forward-word
bindkey "^[[1;5D" backward-word

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

# Load a few important annexes, without Turbo (this is currently required for annexes)
zinit light-mode for \
    zinit-zsh/z-a-patch-dl \
    zinit-zsh/z-a-readurl \
    zinit-zsh/z-a-bin-gem-node

### End of Zinit's installer chunk

# Async
zinit ice pick'async.zsh'
zinit light mafredri/zsh-async

# Theme
[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh
zinit ice depth=1
zinit light romkatv/powerlevel10k

# Plugins > completions
typeset -g ZSH_AUTOSUGGEST_HIGHLIGHT_STYLE='fg=#808080'
# typeset -g ZSH_BASH_COMPLETIONS_FALLBACK_LAZYLOAD_DISABLE='true'

zinit light-mode wait lucid nocd for \
    atinit'ZINIT[COMPINIT_OPTS]=-C; zicompinit; zicdreplay' \
        zdharma/fast-syntax-highlighting \
    atload'!_zsh_autosuggest_start' \
        zsh-users/zsh-autosuggestions \
    blockf \
        zsh-users/zsh-completions \
    blockf \
        3v1n0/zsh-bash-completions-fallback \
    blockf \
        greymd/docker-zsh-completion \
    blockf \
        sudosubin/zsh-github-cli \
    blockf \
        sudosubin/zsh-poetry \
    blockf \
        sudosubin/zsh-pipenv

# Plugins > completions (aws-cli)
zinit ice wait lucid atload'zicdreplay'
zinit snippet https://github.com/aws/aws-cli/blob/v2/bin/aws_zsh_completer.sh

# Plugins > completions (pass otp)
zinit ice wait lucid
zinit light tadfisher/pass-otp

# Plugins > completions (asdf)
# typeset -g JAVA_HOME="$HOME/.asdf/plugins/java/set-java-home.zsh"
zinit ice wait lucid pick'asdf.plugin.zsh' \
    atinit'autoload bashcompinit; bashcompinit' \
    atload'zicdreplay' blockf
zinit light kiurchv/asdf.plugin.zsh

# Plugins > auto-pair
zinit ice wait lucid
zinit light hlissner/zsh-autopair

# Plugins > auto-update
zinit ice wait lucid pick'update.sh'
zinit light sudosubin/zsh-auto-update

# Plugins > fzf
typeset -g FZF_DEFAULT_OPTS='
    --color=dark
    --color=fg:-1,bg:-1,hl:#98c379
    --color=fg+:#ffffff,bg+:#282c34,hl+:#98c379
    --color=info:#e5c07b,prompt:#98c379,pointer:#56b6c2
    --color=marker:#56b6c2,spinner:#e5c07b,header:#56b6c2
'
zinit ice wait lucid pick'shell/key-bindings.zsh' src'shell/completion.zsh'
zinit light junegunn/fzf

# Plugins > k
alias l=k
alias ls='k -a'
zinit ice wait lucid pick'k.sh'
zinit light supercrabtree/k

# Softwares > bat
alias bat=batcat

# Softwares > code
alias code=codium

# Paths > spicetify
export SPICETIFY_INSTALL="$HOME/spicetify-cli"
export PATH="$SPICETIFY_INSTALL:$PATH"

# Functions > activate-virtualenv
activate() {
    local venv_path;
    venv_path=$(pwd);

    while [[ $venv_path != "$HOME" ]]; do
        if [[ -f "$venv_path/.venv/bin/activate" ]]; then
            # shellcheck disable=SC1090
            source "$venv_path/.venv/bin/activate";
            export OPENSSL_CONF="$HOME/.ssl/openssl.cnf";
            break;
        fi
        venv_path="$(readlink -f "$venv_path"/..)";
    done
}
