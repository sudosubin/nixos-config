{
  description = "Nix Configurations";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable-small";
    nixos-hardware.url = "github:nixos/nixos-hardware";
    flake-compat.url = "github:edolstra/flake-compat";
    flake-utils.url = "github:numtide/flake-utils?rev=13faa43c34c0c943585532dacbb457007416d50b";

    nix-darwin = {
      url = "github:nix-darwin/nix-darwin";
      inputs.nixpkgs.follows = "nixpkgs";
    };

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

    nixvim = {
      url = "github:nix-community/nixvim";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    nix-chrome-extensions = {
      url = "github:sudosubin/nix-chrome-extensions";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.flake-compat.follows = "flake-compat";
    };

    nix-vscode-extensions = {
      url = "github:nix-community/nix-vscode-extensions";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.flake-utils.follows = "flake-utils";
      inputs.flake-compat.follows = "flake-compat";
    };

    nixos-config-private-daangn = {
      url = "git+ssh://git@github.com/sudosubin/nixos-config-private?ref=main&dir=daangn";
      # url = "path:/Users/elvin/Code/github.com/sudosubin/nixos-config-private/daangn";
    };

    nixos-config-private-sudosubin = {
      url = "git+ssh://git@github.com/sudosubin/nixos-config-private?ref=main&dir=sudosubin";
      # url = "path:/Users/elvin/Code/github.com/sudosubin/nixos-config-private/sudosubin";
    };
  };

  outputs = { self, nixpkgs, nixos-hardware, nix-darwin, home-manager, ... }@inputs:
    let
      dev-shell = import ./libraries/dev-shell { inherit inputs; };
      home-manager-shared = ./libraries/home-manager;
      nixpkgs-shared = ./libraries/nixpkgs;

    in
    dev-shell // {
      darwinConfigurations.darwin = nix-darwin.lib.darwinSystem {
        system = "aarch64-darwin";
        modules = [
          home-manager-shared
          nixpkgs-shared
          home-manager.darwinModules.home-manager
          ./modules/shared/configuration.nix
          ./modules/darwin/configuration.nix
          ./modules/darwin/home.nix
        ];
        specialArgs = { inherit inputs; };
      };

      nixosConfigurations.linux = nixpkgs.lib.nixosSystem {
        system = "x86_64-linux";
        modules = [
          home-manager-shared
          nixpkgs-shared
          home-manager.nixosModules.home-manager
          ./modules/shared/configuration.nix
          ./modules/linux/configuration.nix
          ./modules/linux/home.nix
        ];
        specialArgs = { inherit inputs; };
      };
    };
}
