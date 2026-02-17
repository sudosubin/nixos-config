{
  config,
  lib,
  ...
}:

{
  imports = [
    ./atuin.nix
    ./eza.nix
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
    settings =
      let
        isEnabled = m: !(m.disabled or false);
        hasConfig = m: (m.config or { }) != { };

        mkModule = name: attrs: { inherit name; } // attrs;

        mkModuleSettings =
          m:
          lib.nameValuePair m.name (
            (m.config or { })
            // lib.optionalAttrs (!isEnabled m) {
              disabled = true;
            }
          );

        modules = [
          (mkModule "username" { })
          (mkModule "hostname" { disabled = true; })
          (mkModule "localip" { disabled = true; })
          (mkModule "directory" {
            config = {
              style = "cyan";
              read_only = " ";
              read_only_style = "red";
            };
          })
          (mkModule "git_branch" {
            config = {
              format = "[$symbol$branch(:$remote_branch)]($style) ";
              style = "purple";
              ignore_bare_repo = false;
            };
          })
          (mkModule "git_commit" {
            config = {
              format = "[($tag ) $hash]($style) ";
              style = "purple";
              tag_disabled = false;
              tag_symbol = "󰓹 ";
            };
          })
          (mkModule "git_state" {
            config.style = "red";
          })
          (mkModule "git_metrics" { })
          (mkModule "git_status" {
            config = {
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
          })
          (mkModule "docker_context" { disabled = true; })
          (mkModule "package" { disabled = true; })
          (mkModule "c" { disabled = true; })
          (mkModule "cpp" { disabled = true; })
          (mkModule "cmake" { disabled = true; })
          (mkModule "xmake" { disabled = true; })
          (mkModule "dart" { disabled = true; })
          (mkModule "deno" { disabled = true; })
          (mkModule "dotnet" { disabled = true; })
          (mkModule "elixir" { disabled = true; })
          (mkModule "elm" { disabled = true; })
          (mkModule "erlang" { disabled = true; })
          (mkModule "fennel" { disabled = true; })
          (mkModule "gleam" { disabled = true; })
          (mkModule "golang" {
            config = {
              format = "[$symbol($version )]($style)";
              symbol = " ";
              style = "cyan";
              not_capable_style = "red";
            };
          })
          (mkModule "haskell" { disabled = true; })
          (mkModule "helm" {
            config = {
              format = "[$symbol($version )]($style)";
              style = "white";
            };
          })
          (mkModule "java" { disabled = true; })
          (mkModule "julia" { disabled = true; })
          (mkModule "kotlin" { disabled = true; })
          (mkModule "kubernetes" {
            config = {
              format = "[$symbol$context( \\($namespace\\))]($style) ";
              style = "blue";
              contexts = [
                {
                  context_pattern = ".*/(?P<name>[\\w-]+)";
                  context_alias = "$name";
                }
              ];
            };
          })
          (mkModule "gradle" { disabled = true; })
          (mkModule "lua" { disabled = true; })
          (mkModule "mojo" { disabled = true; })
          (mkModule "nim" {
            config = {
              format = "[$symbol($version )]($style)";
              symbol = " ";
              style = "yellow";
            };
          })
          (mkModule "nodejs" { disabled = true; })
          (mkModule "ocaml" { disabled = true; })
          (mkModule "perl" { disabled = true; })
          (mkModule "php" { disabled = true; })
          (mkModule "pulumi" { disabled = true; })
          (mkModule "purescript" { disabled = true; })
          (mkModule "python" {
            config = {
              format = "[$symbol(\\($virtualenv\\) )]($style)";
              symbol = " ";
              style = "blue";
              detect_extensions = [ ];
              detect_files = [ ];
            };
          })
          (mkModule "raku" { disabled = true; })
          (mkModule "rlang" { disabled = true; })
          (mkModule "ruby" { disabled = true; })
          (mkModule "rust" {
            config = {
              format = "[$symbol($version )]($style)";
              symbol = " ";
              style = "yellow";
            };
          })
          (mkModule "scala" { disabled = true; })
          (mkModule "solidity" { disabled = true; })
          (mkModule "swift" { disabled = true; })
          (mkModule "terraform" {
            config = {
              format = "[$symbol$version]($style) ";
              symbol = "󱁢 ";
              style = "purple";
            };
          })
          (mkModule "vlang" { disabled = true; })
          (mkModule "vagrant" { disabled = true; })
          (mkModule "zig" { disabled = true; })
          (mkModule "buf" {
            config.style = "blue";
          })
          (mkModule "bun" { disabled = true; })
          (mkModule "nix_shell" {
            config = {
              format = "[$symbol$state]($style) ";
              symbol = " ";
              style = "cyan";
            };
          })
          (mkModule "conda" { disabled = true; })
          (mkModule "aws" {
            config = {
              format = "[$symbol($profile )(\\[$duration\\] )]($style) ";
              symbol = " ";
              style = "yellow";
            };
          })
          (mkModule "gcloud" { disabled = true; })
          (mkModule "openstack" { disabled = true; })
          (mkModule "azure" {
            config.style = "blue";
          })
          (mkModule "crystal" { disabled = true; })
          (mkModule "sudo" {
            config = {
              format = "[$symbol]($style)";
              symbol = "su ";
              style = "red";
            };
          })
          (mkModule "cmd_duration" {
            config = {
              format = "[ $duration]($style) ";
              style = "yellow";
            };
          })
          (mkModule "line_break" { })
          (mkModule "jobs" {
            config = {
              number_threshold = 1;
              symbol = "";
              style = "blue";
            };
          })
          (mkModule "status" { })
          (mkModule "container" {
            config.style = "red dimmed";
          })
          (mkModule "character" {
            config = {
              success_symbol = "[](green)";
              error_symbol = "[](red)";
              vimcmd_symbol = "[](green)";
              vimcmd_replace_one_symbol = "[](purple)";
              vimcmd_replace_symbol = "[](purple)";
              vimcmd_visual_symbol = "[](yellow)";
            };
          })
        ];
      in
      assert lib.length modules == lib.length (lib.unique (map (m: m.name) modules));
      {
        add_newline = true;
        format = lib.concatMapStrings (m: "\$${m.name}") (lib.filter isEnabled modules);
      }
      // lib.listToAttrs (map mkModuleSettings (lib.filter (m: hasConfig m || !isEnabled m) modules));
  };
}
