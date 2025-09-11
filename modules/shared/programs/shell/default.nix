{
  config,
  pkgs,
  lib,
  ...
}:

{
  imports = [
    ./atuin.nix
    ./fzf.nix
  ];

  home.file = {
    ".hushlogin".text = "";
  };

  home.sessionVariables = {
    # Jetbrains
    _JAVA_AWT_WM_NONREPARENTING = "1";

    # Etc
    LESSHISTFILE = "${config.xdg.cacheHome}/lesshst";
    MYSQL_HISTFILE = "${config.xdg.cacheHome}/mysql_history";
  };

  home.shellAliases = {
    l = "lsd -l";
    ls = "lsd -al";
  };

  programs.bash = {
    enable = true;
    historySize = 1000000;
    historyFileSize = 1000000;
    initExtra = lib.mkOrder 0 ''
      if [ -n "$CLAUDECODE" ]; then
        if command -v direnv >/dev/null 2>&1; then
          eval "$(direnv hook bash)"
          eval "$(DIRENV_LOG_FORMAT= direnv export bash)"
        fi
      fi
    '';
  };

  programs.starship = {
    enable = true;
    settings = {
      add_newline = true;
      format = lib.strings.concatStrings [
        "$username"
        "$hostname"
        "$localip"
        "$shlvl"
        "$singularity"
        "$directory"
        "$vcsh"
        "$fossil_branch"
        "$git_branch"
        "$git_commit"
        "$git_state"
        "$git_metrics"
        "$git_status"
        "$hg_branch"
        "$pijul_channel"
        "$docker_context"
        "$package"
        "$c"
        "$cmake"
        "$cobol"
        "$daml"
        "$dart"
        "$deno"
        "$dotnet"
        "$elixir"
        "$elm"
        "$erlang"
        "$fennel"
        "$golang"
        "$guix_shell"
        "$haskell"
        "$haxe"
        "$helm"
        "$java"
        "$julia"
        "$kotlin"
        "$kubernetes"
        "$gradle"
        "$lua"
        "$nim"
        "$nodejs"
        "$ocaml"
        "$opa"
        "$perl"
        "$php"
        "$pulumi"
        "$purescript"
        "$python"
        "$raku"
        "$rlang"
        "$red"
        "$ruby"
        "$rust"
        "$scala"
        "$solidity"
        "$swift"
        "$terraform"
        "$vlang"
        "$vagrant"
        "$zig"
        "$buf"
        "$nix_shell"
        "$conda"
        "$meson"
        "$spack"
        "$memory_usage"
        "$aws"
        "$gcloud"
        "$openstack"
        "$azure"
        "$env_var"
        "$crystal"
        "$custom"
        "$sudo"
        "$cmd_duration"
        "$line_break"
        "$jobs"
        "$battery"
        "$time"
        "$status"
        "$os"
        "$container"
        "$shell"
        "$character"
      ];
      aws = {
        format = "[$symbol($profile )]($style) ";
        symbol = " ";
        style = "yellow";
      };
      azure.style = "blue";
      battery.disabled = true;
      buf.style = "blue";
      bun.disabled = true;
      c.disabled = true;
      character = {
        success_symbol = "[](green)";
        error_symbol = "[](red)";
        vimcmd_symbol = "[](green)";
        vimcmd_replace_one_symbol = "[](purple)";
        vimcmd_replace_symbol = "[](purple)";
        vimcmd_visual_symbol = "[](yellow)";
      };
      cmake.disabled = true;
      cobol.disabled = true;
      cmd_duration = {
        format = "[ $duration]($style) ";
        style = "yellow";
      };
      conda.disabled = true;
      container.style = "red dimmed";
      crystal.disabled = true;
      daml.disabled = true;
      dart.disabled = true;
      deno.disabled = true;
      directory = {
        style = "cyan";
        read_only = " ";
        read_only_style = "red";
      };
      docker_context.disabled = true;
      dotnet.disabled = true;
      elixir.disabled = true;
      elm.disabled = true;
      erlang.disabled = true;
      fennel.disabled = true;
      fill.disabled = true;
      gcloud.disabled = true;
      git_branch = {
        format = "[$symbol$branch(:$remote_branch)]($style) ";
        style = "purple";
      };
      git_commit = {
        format = "[($tag ) $hash]($style) ";
        style = "purple";
        tag_disabled = false;
        tag_symbol = "󰓹 ";
      };
      git_state = {
        style = "red";
      };
      git_status = {
        format = "([$all_status$ahead_behind]($style) )";
        conflicted = "~$count";
        ahead = "󰁝$count";
        behind = "󰁅$count";
        diverged = "󰁝$ahead_count󰁅$behind_count";
        untracked = "?$count";
        stashed = "*$count";
        modified = "!$count";
        staged = "+$count";
        renamed = "󰁔$count";
        deleted = "-$count";
        style = "red";
      };
      golang = {
        format = "[$symbol($version )]($style)";
        symbol = " ";
        style = "cyan";
        not_capable_style = "red";
      };
      guix_shell.disabled = true;
      gradle.disabled = true;
      haskell.disabled = true;
      haxe.disabled = true;
      helm = {
        format = "[$symbol($version )]($style)";
        style = "white";
      };
      hostname.disabled = true;
      java.disabled = true;
      jobs = {
        number_threshold = 1;
        symbol = "";
        style = "blue";
      };
      julia.disabled = true;
      kotlin.disabled = true;
      kubernetes = {
        format = "[$symbol$context( \\($namespace\\))]($style) ";
        style = "blue";
        contexts = [
          {
            context_pattern = ".*/(?P<name>[\\w-]+)";
            context_alias = "$name";
          }
        ];
        disabled = false;
      };
      lua.disabled = true;
      meson.disabled = true;
      nim = {
        format = "[$symbol($version )]($style)";
        symbol = " ";
        style = "yellow";
      };
      nix_shell = {
        format = "[$symbol$state]($style) ";
        symbol = " ";
        style = "cyan";
      };
      nodejs.disabled = true;
      ocaml.disabled = true;
      opa.disabled = true;
      openstack.disabled = true;
      package.disabled = true;
      perl.disabled = true;
      php.disabled = true;
      pulumi.disabled = true;
      purescript.disabled = true;
      python = {
        format = "[$symbol(\\($virtualenv\\) )]($style)";
        symbol = " ";
        style = "blue";
        detect_extensions = [ ];
        detect_files = [ ];
      };
      rlang.disabled = true;
      raku.disabled = true;
      red.disabled = true;
      ruby.disabled = true;
      rust = {
        format = "[$symbol($version )]($style)";
        symbol = " ";
        style = "yellow";
      };
      scala.disabled = true;
      singularity.disabled = true;
      solidity.disabled = true;
      spack.disabled = true;
      sudo = {
        format = "[$symbol]($style)";
        symbol = "su ";
        style = "red";
        disabled = false;
      };
      swift.disabled = true;
      terraform = {
        format = "[$symbol$version]($style) ";
        symbol = "󱁢 ";
        style = "purple";
      };
      vagrant.disabled = true;
      vlang.disabled = true;
      vcsh.disabled = true;
      zig.disabled = true;
    };
  };

  programs.zoxide = {
    enable = true;
    enableBashIntegration = true;
    enableZshIntegration = false;
  };
}
