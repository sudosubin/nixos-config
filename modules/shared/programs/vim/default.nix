{
  config,
  lib,
  pkgs,
  ...
}:

{
  programs.neovim = {
    defaultEditor = true;
    viAlias = true;
    vimAlias = true;
  };

  programs.lazyvim = {
    enable = true;

    config = {
      # autocmds = ''
      #   vim.api.nvim_create_autocmd("FocusLost", {
      #     command = "silent! wa",
      #     desc = "Auto-save on focus loss",
      #   })
      # '';

      # keymaps = ''
      #   vim.keymap.set("n", "<leader>w", "<cmd>w<cr>", { desc = "Save" })
      # '';

      options = ''
        -- Set up globals
        vim.g.mapleader = " ";
        vim.g.maplocalleader = " ";

        -- Set up options
        vim.opt.breakindent = true;
        vim.opt.clipboard = "unnamedplus";
        vim.opt.cursorline = true;
        vim.opt.expandtab = true;
        vim.opt.ignorecase = true;
        vim.opt.inccommand = "split";
        vim.opt.list = true;
        vim.opt.listchars = "trail:⋅,tab:» ,nbsp:␣";
        vim.opt.number = true;
        vim.opt.relativenumber = true;
        vim.opt.scrolloff = 10;
        vim.opt.shiftwidth = 4;
        vim.opt.showmode = false;
        vim.opt.smartcase = true;
        vim.opt.splitbelow = true;
        vim.opt.splitright = true;
        vim.opt.tabstop = 4;
        vim.opt.termguicolors = true;
        vim.opt.virtualedit = "block";
        vim.opt.wrap = false;
      '';
    };

    plugins = {
      colorscheme = ''
        return {
          {
            "projekt0n/github-nvim-theme",
            config = function()
              require("github-theme").setup({
                options = { transparent = true },
                groups = {
                  github_dark_default = { CursorLine = { bg = "bg2" } },
                },
              })
            end,
          },
          {
            "LazyVim/LazyVim",
            opts = { colorscheme = "github_dark_default" },
          },
        }
      '';

      lsp-config = ''
        return {
          "neovim/nvim-lspconfig",
          opts = function(_, opts)
            -- Add additional LSP configuration here
            return opts
          end,
        }
      '';
    };
    extras = {
      editor = {
        telescope.enable = true;
      };

      lang = {
        docker.enable = true;
        go.enable = true;
        helm.enable = true;
        java.enable = true;
        json.enable = true;
        kotlin.enable = true;
        markdown.enable = true;
        nix.enable = true;
        python.enable = true;
        ruby.enable = true;
        rust.enable = true;
        # sql.enable = true;  # TODO: vim-dadbod hash mismatch
        tailwind.enable = true;
        terraform.enable = true;
        toml.enable = true;
        typescript.enable = true;
        yaml.enable = true;
      };
    };

    extraPackages = with pkgs; [
      tree-sitter
    ];

    treesitterParsers = with pkgs.vimPlugins.nvim-treesitter-parsers; [
    ];

    ignoreBuildNotifications = false;
  };
}
