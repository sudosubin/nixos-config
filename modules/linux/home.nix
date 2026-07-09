{
  pkgs,
  ...
}:

{
  home-manager.useGlobalPkgs = true;
  home-manager.useUserPackages = true;
  home-manager.users.sudosubin =
    { ... }:
    {
      home.username = "sudosubin";
      home.homeDirectory = "/home/sudosubin";

      home.packages = with pkgs; [
        # Development
        curl
        fd
        hadolint
        ijhttp
        sentry
        shfmt
        tree
        wtp

        # Utility
        ripgrep
        unzip
      ];

      imports = [
        # Shared CLI tooling only — no GUI modules on a headless server.
        ../shared/programs/act
        ../shared/programs/ai
        ../shared/programs/aws
        ../shared/programs/bat
        ../shared/programs/container
        ../shared/programs/direnv
        ../shared/programs/git
        ../shared/programs/go
        ../shared/programs/gpg
        ../shared/programs/helix
        ../shared/programs/jq
        ../shared/programs/nix
        ../shared/programs/node
        ../shared/programs/python
        ../shared/programs/rust
        ../shared/programs/shell
        ../shared/programs/sqlit
        ../shared/programs/ssh
        ../shared/programs/terraform
        ../shared/programs/tmux
        ../shared/programs/xdg

        # Removed for headless EC2 (GUI / desktop only):
        #   ../shared/programs/1password  (1Password GUI)
        #   ../shared/programs/figma      (figma-agent)
        #   ../shared/programs/firefox    (browser)
        #   ../shared/programs/slack      (agent-slack)
        #   ../shared/programs/terminal   (wezterm)
        #   ../shared/programs/fonts      (desktop fonts)
        #   ../shared/programs/vscode     (editor GUI)
        #   ../linux/programs/input-method (kime IME)
        #   ../linux/programs/theme        (gtk/cursor theme)
        #   ../linux/programs/wayland      (sway/rofi)
        #   ../linux/programs/zpl-open     (desktop mime handler)
        #
        # Private modules also depend on desktop/secret setup; re-enable
        # once sops age keys are provisioned on the instance:
        #   inputs.nixos-config-private-karrot.homeManagerModules.karrot
        #   inputs.nixos-config-private-sudosubin.homeManagerModules.sudosubin
      ];

      home.stateVersion = "25.05";
    };
}
