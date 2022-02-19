{
  description = "Nix Configurations";

  inputs = {
    nixpkgs = {
      url = "github:nixos/nixpkgs/nixpkgs-unstable";
    };

    flake-utils = {
      url = "github:numtide/flake-utils";
    };

    pre-commit-hooks = {
      url = "github:cachix/pre-commit-hooks.nix";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.flake-utils.follows = "flake-utils";
    };

    darwin = {
      url = "github:lnl7/nix-darwin";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    home-manager = {
      url = "github:nix-community/home-manager";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    home-manager-secrets = {
      url = "github:sudosubin/home-manager-secrets";
      # url = "path:/home/sudosubin/Code/sudosubin/home-manager-secrets";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.flake-utils.follows = "flake-utils";
      inputs.pre-commit-hooks.follows = "pre-commit-hooks";
    };

    nixos-config-private-sudosubin = {
      url = "git+ssh://git@github.com/sudosubin/nixos-config-private?ref=main&dir=sudosubin";
      # url = "path:/home/sudosubin/Code/sudosubin/nixos-config-private/sudosubin";
    };

    nixos-config-private-toss = {
      url = "git+ssh://git@github.com/sudosubin/nixos-config-private?ref=main&dir=toss";
      # url = "path:/home/sudosubin/Code/sudosubin/nixos-config-private/toss";
    };
  };

  outputs = { self, nixpkgs, darwin, home-manager, ... }@inputs:
    let
      dev-shell = import ./libraries/dev-shell { inherit inputs; };
      home-manager-shared = ./libraries/home-manager;
      nixpkgs-shared = ./libraries/nixpkgs;
    in
    {
      darwinConfigurations.darwin = darwin.lib.darwinSystem {
        system = "aarch64-darwin";
        modules = [
          home-manager-shared
          nixpkgs-shared
          home-manager.darwinModules.home-manager
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
          ./modules/linux/configuration.nix
          ./modules/linux/home.nix
        ];
        specialArgs = { inherit inputs; };
      };
    } // dev-shell;
}
