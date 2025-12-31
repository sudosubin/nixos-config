{
  config,
  lib,
  pkgs,
  ...
}:

let
  inherit (pkgs.stdenvNoCC.hostPlatform) isLinux;
  toLua = lib.generators.toLua { };

in
{
  programs.nixvim = {
    enable = true;

    defaultEditor = true;
    viAlias = true;
    vimAlias = true;

    colorscheme = "github_dark_default";

    performance.byteCompileLua = {
      enable = true;
      configs = true;
      initLua = true;
      nvimRuntime = true;
      plugins = true;
    };

    globals = {
      mapleader = " ";
      maplocalleader = " ";
    };

    opts = {
      number = true;
      relativenumber = true;

      clipboard = "unnamedplus";

      splitbelow = true;
      splitright = true;

      list = true;
      listchars = "trail:⋅,tab:» ,nbsp:␣";

      wrap = false;

      expandtab = true;
      shiftwidth = 4;
      tabstop = 4;

      scrolloff = 10;
      virtualedit = "block";

      inccommand = "split";
      cursorline = true;
      ignorecase = true;
      termguicolors = true;
    };

    plugins = {
      lsp = {
        enable = true;
        inlayHints = false;
        servers = {
          nixd.enable = true;
          pyright.enable = true;
          vtsls.enable = true;
        };
      };
      # mini = {
      #   enable = true;
      #   mockDevIcons = true;
      #   modules = { };
      # };
    };

    extraPlugins = with pkgs.vimPlugins; [
      github-nvim-theme
    ];
    extraConfigLuaPre = ''
      require("github-theme").setup(${
        toLua {
          options = {
            transparent = true;
          };
          groups.github_dark_default = {
            CursorLine = {
              bg = "bg2";
            };
          };
        }
      })
    '';
  };
}
