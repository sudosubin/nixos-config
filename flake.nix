{
  description = "sudosubin/nixos-config";

  inputs = {
    firefox-addons = {
      url = "gitlab:rycee/nur-expressions?dir=pkgs/firefox-addons";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    flake-utils.url = "github:numtide/flake-utils?rev=13faa43c34c0c943585532dacbb457007416d50b";

    home-manager = {
      url = "github:nix-community/home-manager";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    home-manager-secrets = {
      url = "github:sudosubin/home-manager-secrets";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.lefthook.follows = "lefthook";
    };

    lefthook = {
      url = "github:sudosubin/lefthook.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    nix-darwin = {
      url = "github:nix-darwin/nix-darwin";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    nix-vscode-extensions = {
      url = "github:nix-community/nix-vscode-extensions";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    nixos-hardware.url = "github:nixos/nixos-hardware";

    nixos-config-private-karrot = {
      url = "git+ssh://git@github.com/sudosubin/nixos-config-private?ref=main&dir=karrot&shallow=1";
      # url = "path:/Users/elvin/Code/github.com/sudosubin/nixos-config-private/karrot";
    };

    nixos-config-private-sudosubin = {
      url = "git+ssh://git@github.com/sudosubin/nixos-config-private?ref=main&dir=sudosubin&shallow=1";
      # url = "path:/Users/elvin/Code/github.com/sudosubin/nixos-config-private/sudosubin";
    };

    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable-small";

    nixvim = {
      url = "github:nix-community/nixvim";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    {
      self,
      home-manager,
      nix-darwin,
      nixpkgs,
      ...
    }@inputs:
    let
      dev-shell = import ./libraries/dev-shell { inherit inputs; };
      home-manager-shared = ./libraries/home-manager;
      nixpkgs-shared = ./libraries/nixpkgs;

      # Fixes https://github.com/nix-community/nix-vscode-extensions/pull/158
      # Create a flake-like structure from patched source
      mkPatchedNixVSCodeExtensions =
        system:
        let
          pkgs = import nixpkgs { inherit system; };
          source = pkgs.applyPatches {
            name = "nix-vscode-extensions-patched";
            src = inputs.nix-vscode-extensions;
            patches = [ ./libraries/nix-vscode-extensions/patches/nix-vscode-extensions-fix-semver.patch ];
          };
        in
        {
          overlays.default = import "${source}/nix/overlay.nix";
        };

    in
    dev-shell
    // {
      darwinConfigurations.darwin = nix-darwin.lib.darwinSystem rec {
        system = "aarch64-darwin";
        modules = [
          home-manager-shared
          nixpkgs-shared
          home-manager.darwinModules.home-manager
          ./modules/shared/configuration.nix
          ./modules/darwin/configuration.nix
          ./modules/darwin/home.nix
        ];
        specialArgs = {
          inputs = inputs // {
            nix-vscode-extensions = mkPatchedNixVSCodeExtensions system;
          };
        };
      };

      nixosConfigurations.linux = nixpkgs.lib.nixosSystem rec {
        system = "x86_64-linux";
        modules = [
          home-manager-shared
          nixpkgs-shared
          home-manager.nixosModules.home-manager
          ./modules/shared/configuration.nix
          ./modules/linux/configuration.nix
          ./modules/linux/home.nix
        ];
        specialArgs = {
          inputs = inputs // {
            nix-vscode-extensions = mkPatchedNixVSCodeExtensions system;
          };
        };
      };
    };
}
