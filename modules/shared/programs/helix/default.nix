{
  config,
  lib,
  pkgs,
  ...
}:

{
  xdg.configFile = {
    "helix/runtime/queries/pyproject/highlights.scm".text = "; inherits: toml";
    "helix/runtime/queries/pyproject/indents.scm".text = "; inherits: toml";
    "helix/runtime/queries/pyproject/injections.scm".text = "; inherits: toml";
    "helix/runtime/queries/pyproject/rainbows.scm".text = "; inherits: toml";
    "helix/runtime/queries/pyproject/textobjects.scm".text = "; inherits: toml";
  };

  programs.helix = {
    enable = true;
    defaultEditor = true;

    settings = {
      theme = "github_dark";
      editor = {
        line-number = "relative";
        cursorline = true;
        whitespace = {
          render = {
            space = "none";
            tab = "all";
            nbsp = "none";
            nnbsp = "none";
            newline = "none";
          };
        };
        indent-guides = {
          render = true;
          character = "╎";
        };
      };
    };

    languages = {
      language-server = {
        kotlin-lsp = {
          command = "kotlin-lsp-wrapper";
        };
        nginx-language-server = {
          command = "nginx-language-server";
        };
        pyright = {
          command = "pyright-langserver";
          args = [ "--stdio" ];
        };
        sqruff = {
          command = "sqruff";
          args = [ "lsp" ];
        };
        tflint = {
          command = "tflint";
          args = [ "--langserver" ];
        };
        vtsls = {
          command = "vtsls";
          args = [ "--stdio" ];
          config = {
            hostInfo = "helix";
            "typescript.tsserver.pluginPaths" = [ "./node_modules" ];
          };
        };
      };

      language = [
        {
          name = "bash";
          auto-format = true;
        }
        {
          name = "css";
          auto-format = true;
          language-servers = [
            "vscode-css-language-server"
            "tailwindcss-ls"
          ];
          formatter = {
            command = "biome";
            args = [
              "format"
              "--indent-style"
              "space"
              "--stdin-file-path"
              "file.css"
            ];
          };
        }
        {
          name = "dockerfile";
          auto-format = true;
        }
        {
          name = "go";
          auto-format = true;
        }
        {
          name = "graphql";
          auto-format = true;
          formatter = {
            command = "biome";
            args = [
              "format"
              "--indent-style"
              "space"
              "--stdin-file-path"
              "file.graphql"
            ];
          };
        }
        {
          name = "hcl";
          auto-format = true;
          language-servers = [
            "terraform-ls"
            "tflint"
          ];
        }
        {
          name = "helm";
          auto-format = true;
        }
        {
          name = "html";
          auto-format = true;
          language-servers = [
            "vscode-html-language-server"
            "tailwindcss-ls"
          ];
          formatter = {
            command = "biome";
            args = [
              "format"
              "--indent-style"
              "space"
              "--stdin-file-path"
              "file.html"
            ];
          };
        }
        {
          name = "java";
          auto-format = true;
          formatter = {
            command = "google-java-format";
            args = [ "-" ];
          };
        }
        {
          name = "javascript";
          auto-format = true;
          language-servers = [
            "vtsls"
            "tailwindcss-ls"
          ];
          formatter = {
            command = "biome";
            args = [
              "format"
              "--indent-style"
              "space"
              "--stdin-file-path"
              "file.js"
            ];
          };
        }
        {
          name = "jsx";
          auto-format = true;
          language-servers = [
            "vtsls"
            "tailwindcss-ls"
          ];
          formatter = {
            command = "biome";
            args = [
              "format"
              "--indent-style"
              "space"
              "--stdin-file-path"
              "file.jsx"
            ];
          };
        }
        {
          name = "json";
          auto-format = true;
          formatter = {
            command = "biome";
            args = [
              "format"
              "--indent-style"
              "space"
              "--stdin-file-path"
              "file.json"
            ];
          };
        }
        {
          name = "kotlin";
          auto-format = true;
          language-servers = [ "kotlin-lsp" ];
          formatter = {
            command = "ktlint";
            args = [
              "--format"
              "--stdin"
            ];
          };
        }
        {
          name = "lua";
          auto-format = true;
          formatter = {
            command = "stylua";
            args = [ "-" ];
          };
        }
        {
          name = "markdown";
          auto-format = false;
        }
        {
          name = "nginx";
          auto-format = true;
          language-servers = [ "nginx-language-server" ];
          formatter = {
            command = "nginxfmt";
            args = [ "-" ];
          };
        }
        {
          name = "nix";
          auto-format = true;
          language-servers = [ "nixd" ];
          formatter = {
            command = "nixfmt";
          };
        }
        {
          name = "prisma";
          auto-format = true;
        }
        {
          name = "protobuf";
          auto-format = true;
        }
        {
          name = "pyproject";
          scope = "source.toml.pyproject";
          language-servers = [ "taplo" ];
          file-types = [ { glob = "pyproject.toml"; } ];
          auto-format = true;
          formatter = {
            command = "sh";
            args = [
              "-c"
              "pyproject-fmt - || true"
            ];
          };
          comment-token = "#";
          indent = {
            tab-width = 2;
            unit = "  ";
          };
          grammar = "toml";
        }
        {
          name = "python";
          auto-format = true;
          language-servers = [ "pyright" ];
          formatter = {
            command = "ruff";
            args = [
              "format"
              "-"
            ];
          };
        }
        {
          name = "ruby";
          auto-format = true;
        }
        {
          name = "rust";
          auto-format = true;
        }
        {
          name = "sql";
          auto-format = true;
          language-servers = [ "sqruff" ];
        }
        {
          name = "toml";
          auto-format = true;
          formatter = {
            command = "taplo";
            args = [
              "format"
              "-"
            ];
          };
        }
        {
          name = "typescript";
          auto-format = true;
          language-servers = [
            "vtsls"
            "tailwindcss-ls"
          ];
          formatter = {
            command = "biome";
            args = [
              "format"
              "--indent-style"
              "space"
              "--stdin-file-path"
              "file.ts"
            ];
          };
        }
        {
          name = "tsx";
          auto-format = true;
          language-servers = [
            "vtsls"
            "tailwindcss-ls"
          ];
          formatter = {
            command = "biome";
            args = [
              "format"
              "--indent-style"
              "space"
              "--stdin-file-path"
              "file.tsx"
            ];
          };
        }
        {
          name = "yaml";
          auto-format = true;
        }
      ];
    };

    extraPackages = with pkgs; [
      bash-language-server # bash
      biome # html, css, javascript, json
      buf # protobuf
      docker-compose-language-service # docker-compose
      dockerfile-language-server # dockerfile
      golangci-lint-langserver # go
      google-java-format # java
      gopls # go
      graphql-language-service-cli # graphql
      helm-ls # helm
      jdt-language-server # java
      kotlin-lsp-wrapper # kotlin
      ktlint # kotlin
      lua-language-server # lua
      marksman # markdown
      nginx-config-formatter # nginx
      nginx-language-server # nginx
      nixd # nix
      nixfmt # nix
      prisma-language-server # prisma
      pyproject-fmt # pyproject
      pyright # python
      ruby-lsp # ruby
      ruff # python
      rust-analyzer # rust
      sqruff # sql
      stylua # lua
      tailwindcss-language-server # tailwindcss
      taplo # toml
      terraform-ls # hcl (terraform)
      vscode-langservers-extracted # css, html, json
      vtsls # javascript, jsx, typescript, tsx
      yaml-language-server # yaml
    ];
  };
}
