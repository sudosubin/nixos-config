{
  config,
  lib,
  pkgs,
  ...
}:

{
  programs.nixvim = {
    enable = true;

    defaultEditor = true;
    viAlias = true;
    vimAlias = true;
    colorscheme = "github_dark_default";

    globals = {
      mapleader = " ";
      maplocalleader = " ";
    };

    opts = {
      number = true;
      relativenumber = true;
      showmode = false;

      clipboard = "unnamedplus";

      splitbelow = true;
      splitright = true;

      list = true;
      listchars = "trail:⋅,tab:» ,nbsp:␣";

      wrap = false;

      expandtab = true;
      shiftwidth = 4;
      tabstop = 4;
      breakindent = true;

      scrolloff = 10;
      virtualedit = "block";

      inccommand = "split";
      cursorline = true;
      ignorecase = true;
      smartcase = true;
      termguicolors = true;
    };

    keymaps = [
      {
        mode = "n";
        key = "<leader>e";
        action = "<cmd>Neotree toggle<cr>";
        options = {
          desc = "Toggle file explorer";
        };
      }
    ];

    # performance.byteCompileLua = {
    #   enable = true;
    #   configs = true;
    #   initLua = true;
    #   nvimRuntime = true;
    #   plugins = true;
    # };

    plugins = {
      blink-cmp = {
        enable = true;
        settings = {
          signature.enabled = true;
        };
      };
      colorizer = {
        enable = true;
        settings = {
          # lazy_load = true;
          filetypes = rec {
            __unkeyed-1 = "*";
            css = html;
            html = {
              css = true;
              tailwind = "both";
              tailwind_opts.update_names = true;
            };
            javascriptreact = html;
            typescriptreact = html;
          };
          user_default_options = {
            names = false;
            RRGGBBAA = true;
          };
        };
      };
      conform-nvim = {
        enable = true;
        settings = {
          formatters = {
            rubocop.command = [
              "bundle"
              "exec"
              "rubocop"
            ];
          };
          formatters_by_ft = rec {
            css = javascript;
            dockerfile = [ "dockerfmt" ];
            go = [
              "gofmt"
              "golangci-lint"
            ];
            graphql = javascript;
            html = javascript;
            java = [ "google-java-format" ];
            javascript = {
              __unkeyed-1 = "biome";
              __unkeyed-2 = "prettier";
              stop_after_first = true;
            };
            javascriptreact = javascript;
            json = javascript;
            kotlin = [ "ktlint" ];
            markdown = [ "markdownlint-cli2" ];
            nginx = [ "nginx-config-formatter" ];
            nix = [ "nixfmt" ];
            proto = [ "buf" ];
            python = [
              "ruff_fix"
              "ruff_format"
              "ruff_organize_imports"
            ];
            ruby = [ "rubocop" ];
            rust = [ "rustfmt" ];
            sh = [ "shfmt" ];
            sql = [
              "sqruff"
            ];
            terraform = [ "terraform_fmt" ];
            toml.__raw = ''
              function(bufnr)
                local formatters = { "taplo" }
                local bufname = vim.api.nvim_buf_get_name(bufnr)
                if bufname:match("pyproject.toml") then
                  table.insert(formatters, "pyproject-fmt")
                end
                return formatters
              end
            '';
            typescript = javascript;
            typescriptreact = javascript;
            yaml = [ "yamlfmt" ];
          };
        };
      };
      floaterm = {
        enable = true;
        settings = {
          width = 0.8;
          height = 0.8;
        };
      };
      gitsigns.enable = true;
      guess-indent.enable = true;
      harpoon = {
        enable = true;
        enableTelescope = true;
        settings.settings = {
          save_on_toggle = true;
          sync_on_ui_close = false;
        };
      };
      java = {
        enable = true;
        settings = {
          spring_boot_tools.enable = true;
        };
        # lazyLoad = {
        #   enable = true;
        #   settings = {
        #     ft = [ "java" ];
        #   };
        # };
      };
      lint = {
        enable = true;
      };
      lsp = {
        enable = true;
        inlayHints = false;
        servers = {
          bashls.enable = true;
          biome.enable = true;
          buf_ls.enable = true;
          cssls.enable = true;
          docker_compose_language_service = {
            enable = true;
            settings = {
              telemetry.telemetryLevel = "off";
            };
          };
          dockerls.enable = true;
          golangci_lint_ls.enable = true;
          gopls.enable = true;
          graphql = {
            enable = true;
            package = pkgs.graphql-language-service-cli;
          };
          helm_ls.enable = true;
          html.enable = true;
          jsonls.enable = true;
          kotlin_lsp = {
            enable = true;
            package = pkgs.kotlin-lsp;
          };
          lua_ls = {
            enable = true;
            settings = {
              Lua.completion.callSnippet = "Both";
            };
          };
          marksman.enable = true;
          nginx_language_server.enable = true;
          nixd.enable = true;
          prismals = {
            enable = true;
            package = pkgs.prisma-language-server;
          };
          pyright.enable = true;
          ruby_lsp.enable = true;
          rubocop = {
            enable = true;
            package = null;
            cmd = [
              "bundle"
              "exec"
              "rubocop"
              "--lsp"
            ];
          };
          ruff.enable = true;
          rust_analyzer = {
            enable = true;
            installCargo = true;
            installRustc = true;
            installRustfmt = true;
          };
          sqruff.enable = true;
          tailwindcss.enable = true;
          taplo.enable = true;
          terraformls.enable = true;
          tflint.enable = true;
          vtsls.enable = true;
          yamlls.enable = true;
        };
      };
      mini = {
        enable = true;
        mockDevIcons = true;
        modules = {
          ai = { };
          icons.mockDevIcons = true;
          surround = { };
          statusline = {
            use_icons = true;
            section_location.__raw = "function() return '%l:%-2v' end";
          };
        };
      };
      neo-tree = {
        enable = true;
        settings = {
          window = {
            position = "left";
            width = 30;
          };
          filesystem = {
            filtered_items = {
              visible = true;
            };
            follow_current_file = {
              enabled = true;
              leave_dirs_open = true;
            };
            use_libuv_file_watcher = true;
          };
        };
      };
      telescope = {
        enable = true;
        extensions = {
          fzf-native.enable = true;
          ui-select = {
            enable = true;
            settings = {
              specific_opts.codeactions = false;
            };
          };
        };
        settings = {
          defaults = { };
        };
      };
      treesitter = {
        enable = true;
        highlight.enable = true;
        indent.enable = true;
        # folding.enable = true;
        grammarPackages = with pkgs.vimPlugins.nvim-treesitter.builtGrammars; [
          bash
          css
          diff
          dockerfile
          go
          gomod
          gosum
          gotmpl
          gowork
          graphql
          hcl
          helm
          html
          http
          java
          javascript
          json
          kotlin
          lua
          make
          markdown
          markdown_inline
          nginx
          nix
          prisma
          proto
          python
          regex
          ruby
          rust
          sql
          toml
          tsx
          typescript
          xml
          yaml
        ];
      };
      which-key = {
        enable = true;
        settings = {
          delay = 0;
        };
      };
    };

    extraPackages = with pkgs; [
      buf # required by plugins.conform-nvim.settings.formatters_by_ft.proto
      dockerfmt # required by plugins.conform-nvim.settings.formatters_by_ft.dockerfile
      google-java-format # required by plugins.conform-nvim.settings.formatters_by_ft.java
      ktlint # required by plugins.conform-nvim.settings.formatters_by_ft.kotlin
      markdownlint-cli2 # required by plugins.conform-nvim.settings.formatters_by_ft.markdown
      nginx-config-formatter # required by plugins.conform-nvim.settings.formatters_by_ft.nginx
      nixfmt # required by plugins.conform-nvim.settings.formatters_by_ft.nix
      pyproject-fmt # required by plugins.conform-nvim.settings.formatters_by_ft.toml
      ruby-lsp-rails # required by plugins.lsp.servers.ruby_lsp
      rustfmt # required by plugins.conform-nvim.settings.formatters_by_ft.rust
      shfmt # required by plugins.conform-nvim.settings.formatters_by_ft.sh
      sqruff # required by plugins.conform-nvim.settings.formatters_by_ft.sql
      taplo # required by plugins.conform-nvim.settings.formatters_by_ft.toml
      wget # required by plugins.java
      yamlfmt # required by plugins.conform-nvim.settings.formatters_by_ft.yaml
      # go # required by plugins.conform-nvim.settings.formatters_by_ft.go (will be installed at each project using direnv)
      # golangci-lint # required by plugins.conform-nvim.settings.formatters_by_ft.go (will be installed at each project using direnv)
      # terraform # required by plugins.conform-nvim.settings.formatters_by_ft.terraform (will be installed at each project using direnv)
    ];

    extraPlugins = with pkgs.vimPlugins; [
      github-nvim-theme
      plenary-nvim
      spring-boot-nvim
    ];

    extraConfigLuaPre = ''
      require("github-theme").setup({
        options = {
          transparent = true,
        },
        groups = {
          github_dark_default = {
            CursorLine = {
              bg = "bg2",
            },
          },
        },
      })
    '';
  };
}
