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

    nix-darwin = {
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

  outputs =
    { self
    , nixpkgs
    , flake-utils
    , pre-commit-hooks
    , nix-darwin
    , home-manager
    , home-manager-secrets
    , nixos-config-private-sudosubin
    , nixos-config-private-toss
    , ...
    }: {
      nixosConfigurations.darwin = nix-darwin.lib.darwinSystem {
        system = "x86_64-darwin";
        modules = [
          home-manager.darwinModules.home-manager
        ];
      };

      nixosConfigurations.linux = nixpkgs.lib.nixosSystem {
        system = "x86_64-linux";
        modules = [
          home-manager.nixosModules.home-manager
          {
            home-manager.users.sudosubin.imports = [
              ./modules/shared/home-manager
              home-manager-secrets.homeManagerModules.home-manager-secrets
              nixos-config-private-sudosubin.homeManagerModules.sudosubin
              nixos-config-private-toss.homeManagerModules.toss
            ];
          }
          ./modules/linux/configuration.nix
          ./modules/linux/home.nix
        ];
      };
    } // flake-utils.lib.eachDefaultSystem (system:
    {
      checks = {
        pre-commit-check = pre-commit-hooks.lib.${system}.run {
          src = ./.;
          hooks = {
            nixpkgs-fmt.enable = true;
          };
        };
      };
      devShell = nixpkgs.legacyPackages.${system}.mkShell {
        inherit (self.checks.${system}.pre-commit-check) shellHook;
      };
    }
    );
}
