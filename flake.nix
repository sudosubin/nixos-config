{
  description = "Nix Configurations";

  inputs = {
    nixpkgs = {
      url = "github:nixos/nixpkgs/nixpkgs-unstable";
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
    };
  };

  outputs = {
    self,
    nixpkgs,
    darwin,
    home-manager,
    home-manager-secrets,
    ...
  }: {
    nixosConfigurations.darwin = darwin.lib.darwinSystem {
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
            home-manager-secrets.homeManagerModules.home-manager-secrets
          ];
        }
        ./modules/linux/configuration.nix
        ./modules/linux/home.nix
      ];
    };
  };
}
